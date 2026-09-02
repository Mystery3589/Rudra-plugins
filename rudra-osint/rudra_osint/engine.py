"""Core investigation engine coordinating modules and live UI."""

from __future__ import annotations

import re
import socket
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from rudra_osint.config import REPORTS_DIR
from rudra_osint.modules.active import run_active_probe
from rudra_osint.modules.domain import analyze_domain
from rudra_osint.modules.identity import scan_username
from rudra_osint.modules.media import analyze_media_file
from rudra_osint.modules.network import lookup_ip_intelligence
from rudra_osint.modules.relations import build_relationships
from rudra_osint.reporters.json_out import generate_json_report
from rudra_osint.reporters.markdown import generate_markdown_report

console = Console()

_IP_RE = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
_DOMAIN_RE = re.compile(r"^(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}$")


def _detect_target_type(target: str) -> str:
    """Detect if the target is a media file, IP, domain, or username."""
    if Path(target).is_file() or target.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".tiff")):
        return "media"
    clean = target.strip().replace("https://", "").replace("http://", "").split("/")[0]
    if _IP_RE.match(clean):
        return "ip"
    if _DOMAIN_RE.match(clean):
        return "domain"
    return "username"


def run_investigation(
    target: str,
    level: str = "legal-deep",
    platform_hint: Optional[str] = None,
    output_dir: Optional[Path] = None,
    open_report: bool = False,
) -> tuple[Path, Path]:
    """Execute multi-tier OSINT investigation and output rich results & dossier."""
    target_type = _detect_target_type(target)
    out_dir = output_dir or REPORTS_DIR
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_target = re.sub(r"[^a-zA-Z0-9_-]", "_", target.split("/")[-1])
    md_path = out_dir / f"osint_{clean_target}_{level}_{timestamp}.md"
    json_path = out_dir / f"osint_{clean_target}_{level}_{timestamp}.json"

    # Header Panel
    console.print(
        Panel.fit(
            f"[bold cyan]🕵️ Rudra OSINT Investigation[/bold cyan]\n"
            f"[dim]Target:[/dim] [bold white]{target}[/bold white]  "
            f"[dim]Type:[/dim] [green]{target_type}[/green]  "
            f"[dim]Level:[/dim] [yellow]{level.upper()}[/yellow]",
            border_style="cyan",
        )
    )

    # Active Probe Warning
    if level == "deep":
        console.print(
            Panel(
                "[bold red]⚠️  WARNING: ACTIVE PROBE LEVEL SELECTED[/bold red]\n"
                "[yellow]This mode sends active network packets and scans ports directly against the target.\n"
                "Ensure you own this system or have explicit written authorization.[/yellow]",
                border_style="red",
            )
        )
        if not typer.confirm("Do you wish to proceed with active network probing?", default=False):
            console.print("[dim]Aborted active scan.[/dim]")
            raise typer.Exit(0)

    social_hits = None
    relations = None
    media_intel = None
    domain_intel = None
    ip_intel = None
    active_intel = None

    # Multi-step progress HUD
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    ) as progress:

        # ── 1. Media Investigation ──
        if target_type == "media":
            task = progress.add_task("Analyzing file metadata and GPS...", total=100)
            media_intel = analyze_media_file(target)
            progress.update(task, completed=100)

        # ── 2. Username / Person Investigation ──
        elif target_type == "username":
            task = progress.add_task("Hunting profiles across 60+ platforms...", total=100)

            def _progress_cb(done, total, p_name):
                pct = int((done / total) * 100)
                progress.update(task, completed=pct, description=f"Scanning {p_name} ({done}/{total})...")

            social_hits = scan_username(target, platform_hint=platform_hint, progress_callback=_progress_cb)

            if level in ("legal-deep", "deep"):
                progress.update(task, description="Building relationship & association graph...")
                relations = build_relationships(target, social_hits)

            progress.update(task, completed=100)

        # ── 3. Domain Investigation ──
        elif target_type == "domain":
            task = progress.add_task("Querying DNS, Certificate Transparency & Web Archives...", total=100)
            domain_intel = analyze_domain(target, deep_subdomains=(level != "basic"))
            if domain_intel.ip_addresses:
                ip_intel = lookup_ip_intelligence(domain_intel.ip_addresses[0])
            progress.update(task, completed=100)

        # ── 4. IP Investigation ──
        elif target_type == "ip":
            task = progress.add_task("Querying IP Geolocation, ASN, and ISP routing...", total=100)
            ip_intel = lookup_ip_intelligence(target)
            progress.update(task, completed=100)

        # ── 5. Active Recon (if --deep) ──
        if level == "deep" and target_type in ("domain", "ip"):
            active_task = progress.add_task("Active service fingerprinting & security endpoint scan...", total=100)
            active_intel = run_active_probe(target)
            progress.update(active_task, completed=100)

    # ── Display Live Results ──
    console.print("\n[bold green]✓ Intelligence Gathering Complete![/bold green]\n")

    # 1. Media Results
    if media_intel:
        console.print("[bold]📸 Media & Camera Intelligence:[/bold]")
        console.print(f"  • File: [cyan]{media_intel.file_name}[/cyan] ({media_intel.file_size_bytes / 1024:.1f} KB)")
        if media_intel.camera_make or media_intel.camera_model:
            console.print(f"  • Device: [bold white]{media_intel.camera_make} {media_intel.camera_model}[/bold white]")
        if media_intel.software:
            console.print(f"  • Software: {media_intel.software}")
        if media_intel.gps:
            console.print(f"  • [bold red]📍 GPS Coordinates:[/bold red] [green]{media_intel.gps.latitude:.6f}, {media_intel.gps.longitude:.6f}[/green]")
            if media_intel.gps.resolved_address:
                console.print(f"  • [bold]Physical Address:[/bold] {media_intel.gps.resolved_address}")
            console.print(f"  • [dim]Google Maps:[/dim] {media_intel.gps.maps_url}")

    # 2. Social Profiles Table
    if social_hits:
        console.print(f"[bold]👤 Identified Profiles ([green]{len(social_hits)}[/green] discovered):[/bold]")
        table = Table()
        table.add_column("Category", style="cyan")
        table.add_column("Platform", style="bold white")
        table.add_column("Profile URL", style="green")
        for hit in social_hits:
            table.add_row(hit.category, hit.platform, hit.url)
        console.print(table)

    # 3. Relations Summary
    if relations and (relations.collaborators or relations.associated_orgs):
        console.print("\n[bold]🔗 Relationship & Association Graph:[/bold]")
        if relations.associated_orgs:
            console.print(f"  • Organizations: [cyan]{', '.join(relations.associated_orgs)}[/cyan]")
        if relations.collaborators:
            console.print(f"  • Collaborators: [yellow]{', '.join(relations.collaborators)}[/yellow]")
        if relations.location:
            console.print(f"  • Location: {relations.location}")

    # 4. Domain & Subdomains
    if domain_intel:
        console.print(f"\n[bold]🌐 Domain Intelligence for {domain_intel.domain}:[/bold]")
        if domain_intel.ip_addresses:
            console.print(f"  • IPs: {', '.join(domain_intel.ip_addresses)}")
        if domain_intel.subdomains:
            console.print(f"  • Discovered Subdomains: [bold cyan]{len(domain_intel.subdomains)}[/bold cyan]")
            for sub in domain_intel.subdomains[:10]:
                console.print(f"    - {sub}")
            if len(domain_intel.subdomains) > 10:
                console.print(f"    [dim]... and {len(domain_intel.subdomains) - 10} more in report[/dim]")

    # 5. IP & Geolocation
    if ip_intel:
        console.print(f"\n[bold]📍 Network Location:[/bold] {ip_intel.city}, {ip_intel.country} (ISP: {ip_intel.isp}, ASN: {ip_intel.asn})")

    # 6. Active Probe
    if active_intel and active_intel.open_ports:
        console.print(f"\n[bold red]⚡ Active Open Ports ({len(active_intel.open_ports)}):[/bold red]")
        for p in active_intel.open_ports:
            console.print(f"  • Port {p['port']} ({p['service']}) - {p.get('version', '')}")

    # Compile Reports
    generate_markdown_report(
        target=target,
        level=level,
        output_path=md_path,
        social_hits=social_hits,
        relations=relations,
        media_intel=media_intel,
        domain_intel=domain_intel,
        ip_intel=ip_intel,
        active_intel=active_intel,
    )
    generate_json_report(
        target=target,
        level=level,
        output_path=json_path,
        social_hits=social_hits,
        relations=relations,
        media_intel=media_intel,
        domain_intel=domain_intel,
        ip_intel=ip_intel,
        active_intel=active_intel,
    )

    console.print("\n" + "─" * 60)
    console.print(f"[bold green]📄 Dossier Saved:[/bold green] [cyan]{md_path}[/cyan]")
    console.print(f"[dim]JSON Data: {json_path}[/dim]")

    if open_report:
        editor = os.environ.get("EDITOR", "xdg-open")
        subprocess.run([editor, str(md_path)])

    return md_path, json_path
