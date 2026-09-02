"""CLI command entrypoints for rudra osint."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from rudra_osint.config import REPORTS_DIR
from rudra_osint.engine import run_investigation

console = Console()
app = typer.Typer(
    name="osint",
    help="Multi-tier OSINT & investigation engine — profiling, media/GPS geolocation, relationship mapping, domain intelligence.",
    no_args_is_help=True,
)


@app.command(name="scan")
def scan_cmd(
    target: Annotated[str, typer.Argument(help="Target username, domain, IP, or media file path.")],
    basic: Annotated[bool, typer.Option("--basic", "-b", help="Level 1: Fast surface scan, zero target contact.")] = False,
    legal_deep: Annotated[bool, typer.Option("--legal-deep", "-l", help="Level 2 (Default): Deep passive public intelligence gathering across 60+ platforms.")] = True,
    deep: Annotated[bool, typer.Option("--deep", "-d", help="Level 3: Active network and infrastructure reconnaissance (requires confirmation).")] = False,
    platform: Annotated[Optional[str], typer.Option("--platform", "-p", help="Anchor platform hint (e.g. github, reddit, twitter).")] = None,
    output: Annotated[Optional[Path], typer.Option("--output", "-o", help="Custom directory to save investigation reports.")] = None,
    open_report: Annotated[bool, typer.Option("--open", help="Open the generated markdown report upon completion.")] = False,
):
    """Run an OSINT investigation on a target (domain, handle, IP, or media)."""
    level = "deep" if deep else ("basic" if basic else "legal-deep")
    run_investigation(
        target=target,
        level=level,
        platform_hint=platform,
        output_dir=output,
        open_report=open_report,
    )


@app.command(name="user")
def user_cmd(
    username: Annotated[str, typer.Argument(help="Target username or handle.")],
    basic: Annotated[bool, typer.Option("--basic", "-b", help="Level 1: Quick check on top 10 platforms.")] = False,
    deep: Annotated[bool, typer.Option("--deep", "-d", help="Level 3: Active probing.")] = False,
    platform: Annotated[Optional[str], typer.Option("--platform", "-p", help="Specific platform to start from (e.g. github).")] = None,
    open_report: Annotated[bool, typer.Option("--open", help="Open generated report.")] = False,
):
    """Hunt username footprint and build relationship connections."""
    level = "deep" if deep else ("basic" if basic else "legal-deep")
    run_investigation(target=username, level=level, platform_hint=platform, open_report=open_report)


@app.command(name="domain")
def domain_cmd(
    domain: Annotated[str, typer.Argument(help="Target domain name (e.g. example.com).")],
    basic: Annotated[bool, typer.Option("--basic", "-b", help="Level 1: Fast DNS & WHOIS.")] = False,
    deep: Annotated[bool, typer.Option("--deep", "-d", help="Level 3: Active port & endpoint probing.")] = False,
    open_report: Annotated[bool, typer.Option("--open", help="Open generated report.")] = False,
):
    """Investigate domain infrastructure, Certificate Transparency subdomains, and web archives."""
    level = "deep" if deep else ("basic" if basic else "legal-deep")
    run_investigation(target=domain, level=level, open_report=open_report)


@app.command(name="ip")
def ip_cmd(
    ip: Annotated[str, typer.Argument(help="Target IP address.")],
    deep: Annotated[bool, typer.Option("--deep", "-d", help="Level 3: Active port probe.")] = False,
    open_report: Annotated[bool, typer.Option("--open", help="Open generated report.")] = False,
):
    """Geolocate and analyze network ASN, ISP, and routing for an IP."""
    level = "deep" if deep else "legal-deep"
    run_investigation(target=ip, level=level, open_report=open_report)


@app.command(name="media")
def media_cmd(
    file_path: Annotated[str, typer.Argument(help="Path to an image or video file.")],
    open_report: Annotated[bool, typer.Option("--open", help="Open generated report.")] = False,
):
    """Extract Exif metadata, camera parameters, and GPS coordinates from a media file."""
    run_investigation(target=file_path, level="legal-deep", open_report=open_report)


@app.command(name="reports")
def list_reports_cmd():
    """List all saved OSINT investigation dossiers."""
    if not REPORTS_DIR.exists():
        console.print("[yellow]No reports directory found.[/yellow]")
        return

    reports = sorted(REPORTS_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not reports:
        console.print("[dim]No investigation dossiers recorded yet.[/dim]")
        return

    table = Table(title=f"Saved OSINT Dossiers ({REPORTS_DIR})")
    table.add_column("Report File", style="cyan")
    table.add_column("Size", style="green")
    table.add_column("Modified", style="dim")

    for r in reports:
        size_kb = r.stat().st_size / 1024
        mtime = datetime.fromtimestamp(r.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        table.add_row(r.name, f"{size_kb:.1f} KB", mtime)

    console.print(table)
