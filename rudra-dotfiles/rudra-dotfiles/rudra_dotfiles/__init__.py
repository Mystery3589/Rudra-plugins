"""rudra-dotfiles: Multi-profile dotfiles manager with automatic live backup.

Registers 'dotfiles' (primary) and 'dot' (alias) subcommands.
"""

import typer
from rudra_dotfiles.cli import app as dotfiles_app


def register(app: typer.Typer) -> None:
    """Called by Rudra at startup."""
    app.add_typer(dotfiles_app, name="dotfiles", help="📦 Multi-profile dotfile manager & config switcher.")
    app.add_typer(dotfiles_app, name="dot",      help="📦 Alias for 'rudra dotfiles'.")
