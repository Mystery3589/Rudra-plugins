"""rudra-theme plugin initialization and command registration."""

from __future__ import annotations

import typer

from rudra_theme.cli import app as theme_app


def register(main_app: typer.Typer) -> None:
    """Register the theme subcommand group onto Rudra's main app."""
    main_app.add_typer(theme_app, name="theme", help="Theme & visual styling engine for Rudra.")
