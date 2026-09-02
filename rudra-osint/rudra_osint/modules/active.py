"""Active network reconnaissance and infrastructure probing (Level 3 --deep)."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field

from rich.console import Console

console = Console()


@dataclass
class ActiveProbeIntel:
    target: str
    open_ports: list[dict[str, str]] = field(default_factory=list)
    web_security_endpoints: dict[str, str] = field(default_factory=dict)
    server_banners: list[str] = field(default_factory=list)
    traceroute_hops: list[str] = field(default_factory=list)


def run_active_probe(target_host: str) -> ActiveProbeIntel:
    """Execute active port, banner, and network path scan with nmap."""
    intel = ActiveProbeIntel(target=target_host)

    # 1. Fast service and port detection
    try:
        r = subprocess.run(
            ["nmap", "-F", "-sV", "-T4", target_host],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if r.returncode == 0:
            for line in r.stdout.splitlines():
                if "/tcp" in line or "/udp" in line:
                    parts = line.split()
                    if len(parts) >= 3:
                        port_proto = parts[0]
                        state = parts[1]
                        service = parts[2]
                        version = " ".join(parts[3:]) if len(parts) > 3 else ""
                        intel.open_ports.append({
                            "port": port_proto,
                            "state": state,
                            "service": service,
                            "version": version,
                        })
    except Exception:
        pass

    # 2. Check security endpoints: robots.txt, security.txt
    import urllib.request
    endpoints = [
        ("robots.txt", f"http://{target_host}/robots.txt"),
        ("security.txt", f"http://{target_host}/.well-known/security.txt"),
    ]
    for name, ep_url in endpoints:
        try:
            req = urllib.request.Request(ep_url, headers={"User-Agent": "RudraOSINT/1.0"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                if resp.status == 200:
                    content = resp.read(1000).decode("utf-8", errors="replace")
                    intel.web_security_endpoints[name] = content.strip()
        except Exception:
            pass

    return intel
