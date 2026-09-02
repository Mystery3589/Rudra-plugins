"""Network, IP Geolocation, ASN, and ISP routing intelligence."""

from __future__ import annotations

import json
import socket
import urllib.request
from dataclasses import dataclass
from typing import Optional

from rudra_osint.config import USER_AGENT


@dataclass
class IPIntel:
    ip: str
    hostname: str = ""
    country: str = ""
    country_code: str = ""
    region: str = ""
    city: str = ""
    zip_code: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    timezone: str = ""
    isp: str = ""
    org: str = ""
    asn: str = ""
    maps_url: str = ""


def lookup_ip_intelligence(target_ip: str) -> Optional[IPIntel]:
    """Gather geolocation, ASN, ISP, and reverse DNS info for an IP address."""
    clean_ip = target_ip.strip()

    # 1. Reverse DNS
    hostname = ""
    try:
        hostname = socket.gethostbyaddr(clean_ip)[0]
    except Exception:
        pass

    # 2. GeoIP & ASN lookup via public ip-api (free passive JSON endpoint)
    url = f"http://ip-api.com/json/{clean_ip}?fields=status,message,country,countryCode,regionName,city,zip,lat,lon,timezone,isp,org,as,query"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("status") == "success":
                lat = data.get("lat", 0.0)
                lon = data.get("lon", 0.0)
                maps_url = f"https://www.google.com/maps?q={lat:.6f},{lon:.6f}" if (lat and lon) else ""

                return IPIntel(
                    ip=clean_ip,
                    hostname=hostname,
                    country=data.get("country", ""),
                    country_code=data.get("countryCode", ""),
                    region=data.get("regionName", ""),
                    city=data.get("city", ""),
                    zip_code=data.get("zip", ""),
                    latitude=lat,
                    longitude=lon,
                    timezone=data.get("timezone", ""),
                    isp=data.get("isp", ""),
                    org=data.get("org", ""),
                    asn=data.get("as", ""),
                    maps_url=maps_url,
                )
    except Exception:
        pass

    if hostname:
        return IPIntel(ip=clean_ip, hostname=hostname)

    return None
