"""Passive Attack Surface Discovery.

All sources here are passive / read-only public APIs:
  - Certificate Transparency (crt.sh) — no WAF alerting
  - DNS record enumeration
  - Dangling CNAME / subdomain takeover detection
  - SPF / DMARC email security posture check
  - ASN / IP WHOIS data via ip-api.com
"""
from __future__ import annotations

import json
import re
import socket
import ssl
import time
import urllib.error
import urllib.request
from typing import Any

# ── Helpers ───────────────────────────────────────────────────────────────────

def _fetch_json(url: str, timeout: int = 15) -> Any:
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "rudra-bounty/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", errors="replace"))
    except Exception:
        return None


def _fetch_text(url: str, timeout: int = 10) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "rudra-bounty/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read(65536).decode("utf-8", errors="replace")
    except Exception:
        return ""


def _resolve(host: str) -> str | None:
    try:
        return socket.gethostbyname(host)
    except Exception:
        return None


def _dns_query(host: str, rtype: str) -> list[str]:
    """Use dig for DNS queries."""
    import subprocess
    try:
        r = subprocess.run(
            ["dig", "+short", host, rtype],
            capture_output=True, text=True, timeout=8
        )
        return [l.strip() for l in r.stdout.strip().splitlines() if l.strip()]
    except Exception:
        return []


# ── Dangling CNAME providers ──────────────────────────────────────────────────

_TAKEOVER_SIGNATURES: list[tuple[str, str]] = [
    ("github.io",              "GitHub Pages"),
    ("s3.amazonaws.com",       "AWS S3"),
    ("s3-website",             "AWS S3 website"),
    ("myshopify.com",          "Shopify"),
    ("herokuapp.com",          "Heroku"),
    ("azurewebsites.net",      "Azure Web Apps"),
    ("cloudapp.azure.com",     "Azure CloudApp"),
    ("azurefd.net",            "Azure Front Door"),
    ("trafficmanager.net",     "Azure Traffic Manager"),
    ("ghostio.s3.amazonaws",   "Ghost"),
    ("surge.sh",               "Surge.sh"),
    ("netlify.com",            "Netlify"),
    ("pantheon.io",            "Pantheon"),
    ("helpscoutdocs.com",      "HelpScout"),
    ("zendesk.com",            "Zendesk"),
    ("readme.io",              "ReadMe"),
    ("gitbook.io",             "GitBook"),
    ("fastly.net",             "Fastly"),
    ("cargocollective.com",    "Cargo"),
    ("webflow.io",             "Webflow"),
    ("wpengine.com",           "WP Engine"),
    ("mailchimp.com",          "Mailchimp"),
    ("statuspage.io",          "Statuspage"),
]


def _check_takeover(cname: str) -> str | None:
    """Return provider name if CNAME points to known service, else None."""
    for pattern, provider in _TAKEOVER_SIGNATURES:
        if pattern in cname.lower():
            return provider
    return None


# ── Public Surface Discovery Functions ────────────────────────────────────────

def ct_log_subdomains(domain: str) -> dict[str, Any]:
    """Query crt.sh Certificate Transparency logs for registered subdomains."""
    url = f"https://crt.sh/?q=%.{domain}&output=json"
    data = _fetch_json(url, timeout=20)
    if not data:
        return {"domain": domain, "subdomains": [], "error": "Could not reach crt.sh"}

    seen: set[str] = set()
    for entry in data:
        for name in entry.get("name_value", "").splitlines():
            name = name.strip().lstrip("*.")
            if name and domain in name:
                seen.add(name.lower())

    subdomains = sorted(seen)
    return {"domain": domain, "count": len(subdomains), "subdomains": subdomains}


def dns_profile(domain: str) -> dict[str, Any]:
    """Enumerate DNS records and check for takeover, SPF, DMARC."""
    result: dict[str, Any] = {"domain": domain, "records": {}, "takeover_risks": [], "email_security": {}}

    record_types = ["A", "AAAA", "CNAME", "MX", "TXT", "NS", "CAA", "SOA"]
    for rtype in record_types:
        records = _dns_query(domain, rtype)
        if records:
            result["records"][rtype] = records

    # CNAME takeover detection
    cname_records = result["records"].get("CNAME", [])
    for cname in cname_records:
        provider = _check_takeover(cname)
        if provider:
            ip = _resolve(domain)
            risk_level = "HIGH" if ip is None else "MEDIUM"
            result["takeover_risks"].append({
                "cname": cname,
                "provider": provider,
                "risk": risk_level,
                "resolves": ip is not None,
                "note": "Subdomain resolves — may not be takeable" if ip else "Subdomain does NOT resolve — likely takeover candidate!",
            })

    # SPF check
    txt_records = result["records"].get("TXT", [])
    spf = next((r for r in txt_records if "v=spf1" in r.lower()), None)
    result["email_security"]["spf"] = spf or "MISSING"

    # DMARC check
    dmarc_records = _dns_query(f"_dmarc.{domain}", "TXT")
    dmarc = next((r for r in dmarc_records if "v=dmarc1" in r.lower()), None)
    result["email_security"]["dmarc"] = dmarc or "MISSING"

    return result


def asn_lookup(ip_or_domain: str) -> dict[str, Any]:
    """Look up ASN and network ownership via ip-api.com."""
    host = ip_or_domain.replace("https://", "").replace("http://", "").split("/")[0]
    ip = _resolve(host) if not re.match(r"^\d+\.\d+\.\d+\.\d+$", host) else host
    if not ip:
        return {"error": f"Could not resolve {host}"}

    data = _fetch_json(f"http://ip-api.com/json/{ip}?fields=status,message,country,regionName,city,isp,org,as,query")
    if not data or data.get("status") != "success":
        return {"ip": ip, "error": "ASN lookup failed"}

    return {
        "ip": ip,
        "asn": data.get("as", "—"),
        "isp": data.get("isp", "—"),
        "org": data.get("org", "—"),
        "country": data.get("country", "—"),
        "region": data.get("regionName", "—"),
        "city": data.get("city", "—"),
    }


def whois_lookup(domain: str) -> dict[str, Any]:
    """Basic WHOIS info via RDAP."""
    host = domain.replace("https://", "").replace("http://", "").split("/")[0]
    # Strip to registrable domain
    parts = host.split(".")
    registrable = ".".join(parts[-2:]) if len(parts) >= 2 else host
    data = _fetch_json(f"https://rdap.verisign.com/com/v1/domain/{registrable}", timeout=12)
    if not data:
        data = _fetch_json(f"https://rdap.iana.org/domain/{registrable}", timeout=12)
    if not data:
        return {"domain": registrable, "error": "WHOIS/RDAP lookup failed"}

    result: dict[str, Any] = {"domain": registrable}
    events = {e.get("eventAction", ""): e.get("eventDate", "") for e in data.get("events", [])}
    result["registered"] = events.get("registration", "—")
    result["expires"] = events.get("expiration", "—")
    result["last_changed"] = events.get("last changed", "—")
    result["status"] = [s for s in data.get("status", [])]

    entities = data.get("entities", [])
    for ent in entities:
        roles = ent.get("roles", [])
        vcard = ent.get("vcardArray", [[], []])[1]
        name = next((v[-1] for v in vcard if v[0] == "fn"), None)
        if "registrant" in roles and name:
            result["registrant"] = name
        if "registrar" in roles and name:
            result["registrar"] = name

    return result
