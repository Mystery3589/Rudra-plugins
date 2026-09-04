"""Security posture and configuration auditor.

Performs defensive checks:
  - HTTP security headers (CSP, HSTS, XFO, XCTO, etc.) with posture grading
  - CORS header reflection and credentials policy check
  - TLS/SSL certificate status, expiry, and SANs
  - Standard policy endpoints (security.txt, robots.txt)
  - Technology stack & CDN/WAF identification
"""
from __future__ import annotations

import datetime
import socket
import ssl
import time
import urllib.error
import urllib.request
from typing import Any

SECURITY_HEADERS = {
    "strict-transport-security": {
        "name": "HSTS",
        "weight": 25,
        "advice": "Add 'Strict-Transport-Security: max-age=31536000; includeSubDomains; preload'",
    },
    "content-security-policy": {
        "name": "CSP",
        "weight": 30,
        "advice": "Define Content-Security-Policy to restrict scripts, objects, and framing sources",
    },
    "x-frame-options": {
        "name": "X-Frame-Options",
        "weight": 15,
        "advice": "Set 'X-Frame-Options: DENY' or 'SAMEORIGIN' to protect against clickjacking",
    },
    "x-content-type-options": {
        "name": "X-Content-Type-Options",
        "weight": 10,
        "advice": "Set 'X-Content-Type-Options: nosniff' to prevent MIME-sniffing",
    },
    "referrer-policy": {
        "name": "Referrer-Policy",
        "weight": 10,
        "advice": "Set 'Referrer-Policy: strict-origin-when-cross-origin'",
    },
    "permissions-policy": {
        "name": "Permissions-Policy",
        "weight": 10,
        "advice": "Set 'Permissions-Policy' to disable unused browser APIs (geolocation, camera, etc.)",
    },
}

CDN_WAF_SIGNATURES = [
    ("cf-ray", "Cloudflare"),
    ("server:cloudflare", "Cloudflare"),
    ("x-amz-cf-id", "AWS CloudFront"),
    ("x-cache:hit from cloudfront", "AWS CloudFront"),
    ("x-fastly-request-id", "Fastly"),
    ("server:akamaighost", "Akamai"),
    ("x-azure-ref", "Azure Front Door / CDN"),
    ("x-sucuri-id", "Sucuri WAF"),
    ("server:sucuri", "Sucuri WAF"),
    ("server:gws", "Google Web Server"),
    ("server:nginx", "Nginx"),
    ("server:apache", "Apache"),
    ("x-powered-by:express", "Express.js"),
    ("x-powered-by:next.js", "Next.js"),
    ("x-powered-by:php", "PHP"),
]


def _fetch(url: str, headers: dict[str, str] | None = None, method: str = "GET", timeout: int = 10) -> tuple[int, dict[str, str], str]:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, method=method)
    req.add_header("User-Agent", "rudra-bounty/0.1 (security-audit)")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            hdrs = {k.lower(): v for k, v in resp.getheaders()}
            body = resp.read(32768).decode("utf-8", errors="replace")
            return resp.status, hdrs, body
    except urllib.error.HTTPError as e:
        hdrs = {k.lower(): v for k, v in e.headers.items()} if e.headers else {}
        return e.code, hdrs, ""
    except Exception:
        return 0, {}, ""


def audit_headers(url: str) -> dict[str, Any]:
    """Analyze HTTP response headers and grade security posture."""
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    status, headers, _ = _fetch(url)
    if status == 0:
        return {"url": url, "error": "Could not connect to target"}

    score = 0
    max_score = sum(cfg["weight"] for cfg in SECURITY_HEADERS.values())
    present = {}
    missing = {}

    for header_key, cfg in SECURITY_HEADERS.items():
        if header_key in headers:
            score += cfg["weight"]
            present[cfg["name"]] = headers[header_key]
        else:
            missing[cfg["name"]] = cfg["advice"]

    pct = int((score / max_score) * 100)
    grade = "A+" if pct == 100 else ("A" if pct >= 80 else ("B" if pct >= 65 else ("C" if pct >= 50 else ("D" if pct >= 35 else "F"))))

    # Detect CDN / WAF / Tech from headers
    detected_tech = []
    for sig, label in CDN_WAF_SIGNATURES:
        if ":" in sig:
            k, v = sig.split(":", 1)
            if k in headers and v in headers[k].lower():
                detected_tech.append(label)
        else:
            if sig in headers:
                detected_tech.append(label)

    return {
        "url": url,
        "status_code": status,
        "score": pct,
        "grade": grade,
        "present_headers": present,
        "missing_headers": missing,
        "technologies": sorted(set(detected_tech)),
        "server_header": headers.get("server", "—"),
    }


def audit_cors(url: str) -> dict[str, Any]:
    """Test CORS response to determine origin reflection policies."""
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    test_origins = [
        "https://rudra-test-arbitrary.com",
        "null",
    ]
    findings = []
    for origin in test_origins:
        status, headers, _ = _fetch(url, headers={"Origin": origin}, method="GET")
        if status == 0:
            continue
        acao = headers.get("access-control-allow-origin")
        acac = headers.get("access-control-allow-credentials", "").lower() == "true"

        if acao == origin:
            severity = "HIGH" if acac else "MEDIUM"
            findings.append({
                "origin_tested": origin,
                "acao": acao,
                "credentials_allowed": acac,
                "severity": severity,
                "description": f"Reflects arbitrary Origin '{origin}'" + (" with Allow-Credentials: true!" if acac else "."),
            })
        elif acao == "*":
            findings.append({
                "origin_tested": origin,
                "acao": "*",
                "credentials_allowed": acac,
                "severity": "LOW" if not acac else "HIGH",
                "description": "Wildcard '*' Access-Control-Allow-Origin" + (" with Allow-Credentials (Invalid/Misconfigured)" if acac else "."),
            })

    return {
        "url": url,
        "vulnerable": len(findings) > 0,
        "findings": findings,
    }


def audit_tls(domain: str) -> dict[str, Any]:
    """Inspect SSL/TLS certificate validity, expiration, and Subject Alternative Names."""
    host = domain.replace("https://", "").replace("http://", "").split("/")[0].split(":")[0]
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        with socket.create_connection((host, 443), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert(binary_form=False)
                cipher = ssock.cipher()
                tls_version = ssock.version()

                # If binary_form is False with CERT_NONE, getpeercert may be empty in standard mode;
                # Let's verify with CERT_REQUIRED or fallback to DER parsing:
                if not cert:
                    # Retry with normal validation for details
                    ctx2 = ssl.create_default_context()
                    with socket.create_connection((host, 443), timeout=10) as s2:
                        with ctx2.wrap_socket(s2, server_hostname=host) as ss2:
                            cert = ss2.getpeercert()

                not_after_str = cert.get("notAfter", "")
                not_before_str = cert.get("notBefore", "")
                issuer_tuples = cert.get("issuer", ())
                subject_tuples = cert.get("subject", ())

                issuer = dict(x[0] for x in issuer_tuples).get("organizationName", "—")
                subject = dict(x[0] for x in subject_tuples).get("commonName", "—")
                sans = [v for k, v in cert.get("subjectAltName", []) if k == "DNS"]

                expires = None
                days_left = None
                if not_after_str:
                    exp_dt = datetime.datetime.strptime(not_after_str, "%b %d %H:%M:%S %Y %Z")
                    expires = exp_dt.strftime("%Y-%m-%d")
                    days_left = (exp_dt - datetime.datetime.utcnow()).days

                return {
                    "host": host,
                    "valid": days_left is not None and days_left > 0,
                    "days_remaining": days_left,
                    "expires_date": expires,
                    "subject": subject,
                    "issuer": issuer,
                    "tls_version": tls_version,
                    "cipher": cipher[0] if cipher else "—",
                    "sans_count": len(sans),
                    "sans": sans[:10],
                }
    except Exception as e:
        return {"host": host, "error": str(e)}


def audit_policy_endpoints(domain: str) -> dict[str, Any]:
    """Check standard security and policy files."""
    base = domain if domain.startswith(("http://", "https://")) else f"https://{domain}"
    endpoints = [
        ("/.well-known/security.txt", "security.txt (RFC 9116)"),
        ("/security.txt", "security.txt (legacy)"),
        ("/robots.txt", "robots.txt"),
        ("/sitemap.xml", "sitemap.xml"),
    ]
    results = []
    for path, label in endpoints:
        status, _, body = _fetch(f"{base}{path}", timeout=6)
        if status in (200, 301, 302):
            results.append({
                "path": path,
                "label": label,
                "status": status,
                "snippet": body[:200].replace("\n", " ").strip() if body else "—",
            })
    return {"base_url": base, "endpoints": results}
