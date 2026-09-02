"""rudra-lab plugin — disposable isolated lab environments."""

import typer

from rudra_lab.commands import app


def register(main_app: typer.Typer) -> None:
    """Called by rudra at startup to register the lab command group."""
    main_app.add_typer(app, name="lab", help="Disposable isolated lab environments — sandbox anything safely.")
