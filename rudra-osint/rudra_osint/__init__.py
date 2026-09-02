"""rudra-osint plugin initialization and command registration."""

from __future__ import annotations

import typer

from rudra_osint.cli import app as osint_app


def register(main_app: typer.Typer) -> None:
    """Register the osint subcommand group onto Rudra's main app."""
    main_app.add_typer(osint_app, name="osint", help="Multi-tier OSINT & investigation engine — profiling, media/GPS, subdomains, relationships.")
