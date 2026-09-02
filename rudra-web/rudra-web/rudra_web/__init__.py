"""rudra-web plugin initialization and command registration."""

from __future__ import annotations

import typer

from rudra_web.cli import app as web_app


def register(main_app: typer.Typer) -> None:
    """Register the web subcommand group onto Rudra's main app."""
    main_app.add_typer(web_app, name="web", help="Modern local web interface & dashboard for Rudra.")
