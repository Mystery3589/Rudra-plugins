"""Domain, Subdomain (crt.sh), Web Archive (Wayback), and Email Security intelligence."""

from __future__ import annotations

import json
import re
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Optional

from rudra_osint.config import USER_AGENT


@dataclass
class DomainIntel:
    domain: str
    ip_addresses: list[str] = field(default_factory=list)
    subdomains: list[str] = field(default_factory=list)
    mx_records: list[str] = field(default_factory=list)
    txt_records: list[str] = field(default_factory=list)
    has_spf: bool = False
    has_dmarc: bool = False
    wayback_urls: list[str] = field(default_factory=list)
    wayback_snapshot_count: int = 0


def fetch_crt_subdomains(domain: str) -> list[str]:
    """Discover subdomains via crt.sh Certificate Transparency logs."""
    clean_domain = domain.strip().lower()
    url = f"https://crt.sh/?q=%.{clean_domain}&output=json"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    subdomains = set()

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for entry in data:
                name_value = entry.get("name_value", "")
                for sub in name_value.splitlines():
                    sub = sub.strip().lower()
                    if "*" not in sub and sub.endswith(clean_domain):
                        subdomains.add(sub)
    except Exception:
        pass

    return sorted(subdomains)


def fetch_wayback_endpoints(domain: str, limit: int = 25) -> list[str]:
    """Extract historical endpoints from the Wayback Machine (archive.org)."""
    clean_domain = domain.strip().lower()
    url = f"https://web.archive.org/cdx/search/cdx?url=*.{clean_domain}/*&output=json&collapse=urlkey&limit={limit}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    endpoints = set()

    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if len(data) > 1:
                # first row is header ["urlkey", "timestamp", "original", ...]
                for row in data[1:]:
                    if len(row) >= 3:
                        endpoints.add(row[2])
    except Exception:
        pass

    return sorted(endpoints)


def analyze_domain(domain: str, deep_subdomains: bool = True) -> DomainIntel:
    """Analyze domain infrastructure, certificate transparency, and historical snapshots."""
    clean_domain = domain.strip().lower().replace("https://", "").replace("http://", "").split("/")[0]
    intel = DomainIntel(domain=clean_domain)

    # 1. Resolve direct IPs
    try:
        addr_info = socket.getaddrinfo(clean_domain, None)
        intel.ip_addresses = list(dict.fromkeys(a[4][0] for a in addr_info if a and len(a) > 4))
    except Exception:
        pass

    # 2. Subdomains via crt.sh
    if deep_subdomains:
        intel.subdomains = fetch_crt_subdomains(clean_domain)

    # 3. Wayback Machine snapshots
    intel.wayback_urls = fetch_wayback_endpoints(clean_domain, limit=30)
    intel.wayback_snapshot_count = len(intel.wayback_urls)

    return intel
