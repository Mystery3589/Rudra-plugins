"""rudra-git plugin — advanced git workflow for rudra.

Exposes `rudra git` with subcommands for status, branches, commits,
sync, stash, log, undo, and a set of fun/power automation commands.
"""

import typer

from rudra_git import branch, commit, extras, log, remote, stash, status, sync, undo  # noqa: F401

app = typer.Typer(
    help="Advanced git workflow — status, branches, commits, sync, stash, log, undo, and more.",
    no_args_is_help=True,
)

# Register all submodule commands onto the app
from rudra_git._register import register_all
register_all(app)


def register(main_app: typer.Typer) -> None:
    """Called by rudra at startup."""
    main_app.add_typer(app, name="git", help="Advanced git workflow.")
