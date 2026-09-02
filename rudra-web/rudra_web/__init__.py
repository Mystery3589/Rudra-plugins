"""Rudra Web UI package."""

import typer
from rudra.web.cli import cli_app


def register(main_app: typer.Typer) -> None:
    """Register the web subcommand group onto Rudra's main app."""
    main_app.add_typer(cli_app, name="web", help="🌐 Rudra Terminal Web UI — Schema-Driven Terminal Web Interface.")
