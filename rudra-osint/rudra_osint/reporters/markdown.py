"""Markdown investigation dossier generator."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from rudra_osint.modules.active import ActiveProbeIntel
from rudra_osint.modules.domain import DomainIntel
from rudra_osint.modules.identity import SocialHit
from rudra_osint.modules.media import MediaIntel
from rudra_osint.modules.network import IPIntel
from rudra_osint.modules.relations import TargetRelations


def generate_markdown_report(
    target: str,
    level: str,
    output_path: Path,
    social_hits: Optional[list[SocialHit]] = None,
    relations: Optional[TargetRelations] = None,
    media_intel: Optional[MediaIntel] = None,
    domain_intel: Optional[DomainIntel] = None,
    ip_intel: Optional[IPIntel] = None,
    active_intel: Optional[ActiveProbeIntel] = None,
) -> Path:
    """Generate a clean GitHub-flavored Markdown dossier for the investigation."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines: list[str] = []

    lines.append(f"# 🕵️ Rudra OSINT Investigation Dossier: `{target}`")
    lines.append("")
    lines.append(f"**Target:** `{target}`  ")
    lines.append(f"**Scan Level:** `{level.upper()}`  ")
    lines.append(f"**Generated:** {timestamp}  ")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 1. Executive Summary
    lines.append("## 1. Executive Summary")
    lines.append("")
    summary_points = []
    if social_hits:
        summary_points.append(f"- Discovered **{len(social_hits)} digital profiles** across social/dev platforms.")
    if relations and relations.known_aliases:
        summary_points.append(f"- Identified candidate aliases: **{', '.join(relations.known_aliases)}**")
    if media_intel and media_intel.gps:
        summary_points.append(f"- Extracted exact GPS coordinates: **{media_intel.gps.latitude:.5f}, {media_intel.gps.longitude:.5f}**")
        if media_intel.gps.resolved_address:
            summary_points.append(f"  - Resolved Address: *{media_intel.gps.resolved_address}*")
    if domain_intel and domain_intel.subdomains:
        summary_points.append(f"- Enumerated **{len(domain_intel.subdomains)} subdomains** via Certificate Transparency.")
    if ip_intel:
        summary_points.append(f"- Network: **{ip_intel.ip}** ({ip_intel.city}, {ip_intel.country}) - ISP: `{ip_intel.isp}` / ASN: `{ip_intel.asn}`")
    if active_intel and active_intel.open_ports:
        summary_points.append(f"- Active Probe: Found **{len(active_intel.open_ports)} open ports** on target infrastructure.")

    if not summary_points:
        summary_points.append("- No significant digital footprint detected on standard public channels.")

    lines.extend(summary_points)
    lines.append("")
    lines.append("---")
    lines.append("")

    # 2. Digital Identities & Social Profiles
    if social_hits:
        lines.append("## 2. Identified Digital Profiles")
        lines.append("")
        lines.append("| Category | Platform | Profile URL | Status |")
        lines.append("|---|---|---|---|")
        for hit in social_hits:
            lines.append(f"| {hit.category} | **{hit.platform}** | [{hit.url}]({hit.url}) | Found |")
        lines.append("")
        lines.append("---")
        lines.append("")

    # 3. Relationship & Association Graph
    if relations and (relations.collaborators or relations.associated_orgs or relations.social_links):
        lines.append("## 3. Social Relations & Affiliation Graph")
        lines.append("")
        if relations.bio_text:
            lines.append(f"> **Target Bio:** *{relations.bio_text}*")
            lines.append("")
        if relations.location:
            lines.append(f"- **Declared Location:** `{relations.location}`")
        if relations.associated_orgs:
            lines.append(f"- **Associated Organizations:** {', '.join(f'`{o}`' for o in relations.associated_orgs)}")
        if relations.collaborators:
            lines.append(f"- **Co-authors / Collaborators:** {', '.join(f'`{c}`' for c in relations.collaborators)}")
        if relations.linked_urls:
            lines.append(f"- **Linked Websites:** {', '.join(relations.linked_urls)}")
        lines.append("")
        lines.append("---")
        lines.append("")

    # 4. Media & Geolocation Intelligence
    if media_intel:
        lines.append("## 4. Media & Geolocation Intelligence")
        lines.append("")
        lines.append(f"- **File:** `{media_intel.file_name}` ({media_intel.file_size_bytes / 1024:.1f} KB)")
        if media_intel.camera_make or media_intel.camera_model:
            lines.append(f"- **Device:** `{media_intel.camera_make} {media_intel.camera_model}`")
        if media_intel.software:
            lines.append(f"- **Software / Editor:** `{media_intel.software}`")
        if media_intel.datetime_original:
            lines.append(f"- **Capture Timestamp:** `{media_intel.datetime_original}`")

        if media_intel.gps:
            lines.append("")
            lines.append("### 📍 Geolocation Findings")
            lines.append(f"- **Coordinates:** `{media_intel.gps.latitude:.6f}, {media_intel.gps.longitude:.6f}`")
            if media_intel.gps.resolved_address:
                lines.append(f"- **Physical Location:** {media_intel.gps.resolved_address}")
            lines.append(f"- [Open in Google Maps]({media_intel.gps.maps_url}) | [Open in OpenStreetMap]({media_intel.gps.osm_url})")

        lines.append("")
        lines.append("### 🔍 Reverse Visual Lookups")
        for engine, link in media_intel.reverse_search_links.items():
            lines.append(f"- [{engine}]({link})")
        lines.append("")
        lines.append("---")
        lines.append("")

    # 5. Domain & Infrastructure
    if domain_intel:
        lines.append("## 5. Domain & Subdomain Intelligence")
        lines.append("")
        lines.append(f"- **Domain:** `{domain_intel.domain}`")
        if domain_intel.ip_addresses:
            lines.append(f"- **Resolved IPs:** {', '.join(f'`{ip}`' for ip in domain_intel.ip_addresses)}")

        if domain_intel.subdomains:
            lines.append("")
            lines.append(f"### Discovered Subdomains ({len(domain_intel.subdomains)})")
            lines.append("```")
            for sub in domain_intel.subdomains[:40]:
                lines.append(sub)
            if len(domain_intel.subdomains) > 40:
                lines.append(f"... and {len(domain_intel.subdomains) - 40} more")
            lines.append("```")

        if domain_intel.wayback_urls:
            lines.append("")
            lines.append(f"### Historical Endpoints (Wayback Machine - {len(domain_intel.wayback_urls)} snapshots)")
            for wb in domain_intel.wayback_urls[:15]:
                lines.append(f"- `{wb}`")

        lines.append("")
        lines.append("---")
        lines.append("")

    # 6. Network & IP
    if ip_intel:
        lines.append("## 6. Network & Geolocation")
        lines.append("")
        lines.append(f"- **IP:** `{ip_intel.ip}`")
        if ip_intel.hostname:
            lines.append(f"- **Reverse DNS:** `{ip_intel.hostname}`")
        lines.append(f"- **Location:** {ip_intel.city}, {ip_intel.region}, {ip_intel.country}")
        lines.append(f"- **ISP:** `{ip_intel.isp}`")
        lines.append(f"- **Organization:** `{ip_intel.org}`")
        lines.append(f"- **ASN:** `{ip_intel.asn}`")
        if ip_intel.maps_url:
            lines.append(f"- [Map Location]({ip_intel.maps_url})")
        lines.append("")
        lines.append("---")
        lines.append("")

    # 7. Active Recon (if --deep)
    if active_intel and active_intel.open_ports:
        lines.append("## 7. Active Reconnaissance Findings (Level 3)")
        lines.append("")
        lines.append("| Port | State | Service | Version |")
        lines.append("|---|---|---|---|")
        for p in active_intel.open_ports:
            lines.append(f"| {p['port']} | {p['state']} | {p['service']} | {p.get('version', '')} |")

        if active_intel.web_security_endpoints:
            lines.append("")
            lines.append("### Exposed Web Security Endpoints")
            for ep, text in active_intel.web_security_endpoints.items():
                lines.append(f"**{ep}:**")
                lines.append("```")
                lines.append(text[:300])
                lines.append("```")
        lines.append("")
        lines.append("---")
        lines.append("")

    lines.append("*Report compiled autonomously by Rudra OSINT Engine.*")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path
