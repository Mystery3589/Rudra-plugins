"""Register all rudra-git submodule commands onto the main git Typer app."""

import typer


def register_all(app: typer.Typer) -> None:
    from rudra_git import audit, branch, commit, creative, extras, log, remote, stash, status, sync, undo

    # Each submodule has its own app with @app.command() functions.
    # We add them all onto the main git app.
    for mod in (status, branch, commit, sync, log, undo, stash, remote, extras, audit, creative):
        for cmd_info in mod.app.registered_commands:
            app.registered_commands.append(cmd_info)
        for group in mod.app.registered_groups:
            app.registered_groups.append(group)
