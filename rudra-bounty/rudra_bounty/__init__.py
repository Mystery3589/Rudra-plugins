"""rudra-bounty: Advanced Bug Bounty Hunter plugin for Rudra.

Registers 'hunt' (primary) and 'bounty' (alias) subcommands.
"""

import typer
from rudra_bounty.cli import app as hunt_app


def register(app: typer.Typer) -> None:
    """Called by Rudra at startup."""
    app.add_typer(hunt_app, name="hunt",   help="🎯 Bug bounty hunter — recon, scope, audit, track & report.")
    app.add_typer(hunt_app, name="bounty", help="🎯 Alias for 'rudra hunt'.")
