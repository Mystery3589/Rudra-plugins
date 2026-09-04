"""Bug bounty report generator with CVSS v3.1 calculation.

Generates standard markdown vulnerability reports tailored for
HackerOne, Bugcrowd, and Intigriti platforms.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Optional


def calculate_cvss31(
    av: str = "N",  # Network (N), Adjacent (A), Local (L), Physical (P)
    ac: str = "L",  # Low (L), High (H)
    pr: str = "N",  # None (N), Low (L), High (H)
    ui: str = "N",  # None (N), Required (R)
    s: str = "U",   # Unchanged (U), Changed (C)
    c: str = "L",   # None (N), Low (L), High (H)
    i: str = "L",   # None (N), Low (L), High (H)
    a: str = "N",   # None (N), Low (L), High (H)
) -> tuple[float, str, str]:
    """Calculate CVSS v3.1 Base Score, Vector String, and Severity Rating."""
    av_weights = {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.2}
    ac_weights = {"L": 0.77, "H": 0.44}
    ui_weights = {"N": 0.85, "R": 0.62}
    c_weights = {"N": 0.0, "L": 0.22, "H": 0.56}
    i_weights = {"N": 0.0, "L": 0.22, "H": 0.56}
    a_weights = {"N": 0.0, "L": 0.22, "H": 0.56}

    scope_changed = (s.upper() == "C")
    if scope_changed:
        pr_weights = {"N": 0.85, "L": 0.68, "H": 0.5}
    else:
        pr_weights = {"N": 0.85, "L": 0.62, "H": 0.27}

    iss = 1 - ((1 - c_weights.get(c.upper(), 0.0)) *
               (1 - i_weights.get(i.upper(), 0.0)) *
               (1 - a_weights.get(a.upper(), 0.0)))

    if not scope_changed:
        impact = 6.42 * iss
    else:
        impact = 7.52 * (iss - 0.029) - 3.25 * ((iss - 0.02) ** 15)

    exploitability = (
        8.22 *
        av_weights.get(av.upper(), 0.85) *
        ac_weights.get(ac.upper(), 0.77) *
        pr_weights.get(pr.upper(), 0.85) *
        ui_weights.get(ui.upper(), 0.85)
    )

    if impact <= 0:
        base_score = 0.0
    elif not scope_changed:
        base_score = min(10.0, math.ceil(min(impact + exploitability, 10.0) * 10) / 10)
    else:
        base_score = min(10.0, math.ceil(min(1.08 * (impact + exploitability), 10.0) * 10) / 10)

    if base_score >= 9.0:
        severity = "CRITICAL"
    elif base_score >= 7.0:
        severity = "HIGH"
    elif base_score >= 4.0:
        severity = "MEDIUM"
    elif base_score > 0.0:
        severity = "LOW"
    else:
        severity = "NONE"

    vector_str = f"CVSS:3.1/AV:{av.upper()}/AC:{ac.upper()}/PR:{pr.upper()}/UI:{ui.upper()}/S:{s.upper()}/C:{c.upper()}/I:{i.upper()}/A:{a.upper()}"
    return base_score, vector_str, severity


def generate_report_markdown(
    title: str,
    target: str,
    vulnerability_type: str = "Security Misconfiguration",
    cwe: str = "CWE-16: Configuration",
    severity: str = "MEDIUM",
    cvss_vector: str = "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N",
    cvss_score: float = 5.3,
    summary: str = "",
    steps_to_reproduce: list[str] | None = None,
    impact: str = "",
    remediation: str = "",
    program: str = "",
) -> str:
    """Generate professional bug bounty markdown submission report."""
    steps_md = ""
    if steps_to_reproduce:
        steps_md = "\n".join(f"{idx+1}. {step}" for idx, step in enumerate(steps_to_reproduce))
    else:
        steps_md = "1. Navigate to target endpoint.\n2. Inspect response headers/configuration.\n3. Verify observed discrepancy."

    report = f"""# {title}

**Target Asset:** `{target}`  
**Program:** {program or 'Independent Assessment'}  
**Weakness Classification:** {cwe}  
**Vulnerability Type:** {vulnerability_type}  
**Severity:** **{severity.upper()}** ({cvss_score})  
**CVSS v3.1 Vector:** `{cvss_vector}`  

---

## 1. Summary
{summary or 'A security configuration observation was identified on the target asset.'}

## 2. Vulnerable Asset & Endpoint
- **URL/Host:** `{target}`
- **Classification:** {vulnerability_type}

## 3. Steps to Reproduce
{steps_md}

## 4. Business & Security Impact
{impact or 'Security controls can be undermined if modern defensive standards are not enforced.'}

## 5. Remediation & Recommended Fix
{remediation or 'Implement recommended configuration guidelines per OWASP standards.'}

---
*Report generated via Rudra Bounty Hunter (`rudra hunt report`)*
"""
    return report
