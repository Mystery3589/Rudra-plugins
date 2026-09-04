"""rudra-share: Instant zero-config port sharing and public tunneling plugin for Rudra.

Registers 'share' (primary) and 'tunnel' (alias) subcommands.
"""

import typer
from rudra_share.cli import app as share_app


def register(app: typer.Typer) -> None:
    """Called by Rudra at startup."""
    app.add_typer(share_app, name="share",  help="🌐 Instant zero-config public tunneling & port sharing.")
    app.add_typer(share_app, name="tunnel", help="🌐 Alias for 'rudra share'.")
