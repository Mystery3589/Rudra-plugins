"""rudra-win plugin initialization and command registration."""

from __future__ import annotations

import typer
from rudra_win.cli import app as win_app


def register(main_app: typer.Typer) -> None:
    """Register the win subcommand group onto Rudra's main app."""
    main_app.add_typer(win_app, name="win", help="⚡ Windows Overlord — Debloat, tweak, optimize, and bend Windows to your will.")
