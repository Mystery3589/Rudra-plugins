"""rudra-vault plugin initialization."""

from __future__ import annotations

import typer
from rudra_vault.cli import app as vault_app


def register(main_app: typer.Typer) -> None:
    """Register vault command group onto Rudra CLI."""
    main_app.add_typer(
        vault_app,
        name="vault",
        help="🔐 Secure encrypted Safe & Vault for passwords, API keys, documents, notes, photos, and videos.",
    )
