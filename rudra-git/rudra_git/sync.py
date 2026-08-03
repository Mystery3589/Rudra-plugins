"""rudra git sync / push / pull — sync with remote."""

from __future__ import annotations
from typing import Annotated, Optional
import typer
from rich.console import Console
from rudra_git.helpers import (
    ahead_behind, current_branch, default_branch, git,
    has_remote, is_clean, run, require_repo, short_hash,
)

app = typer.Typer()
console = Console()


@app.command()
def sync(
    push: Annotated[bool, typer.Option("--push", "-p", help="Push after pulling.")] = False,
    rebase: Annotated[bool, typer.Option("--rebase/--merge", help="Rebase or merge when pulling.")] = True,
    remote: Annotated[str, typer.Option("--remote", help="Remote to sync with.")] = "origin",
    branch: Annotated[Optional[str], typer.Option("--branch", "-b", help="Branch to sync.")] = None,
    stash: Annotated[bool, typer.Option("--stash/--no-stash", help="Auto-stash dirty tree before sync.")] = True,
    upstream: Annotated[bool, typer.Option("--upstream", "-u", help="Pull from 'upstream' remote first (fork workflow).")] = False,
    force_push: Annotated[bool, typer.Option("--force", "-f", help="Force-push with lease after sync.")] = False,
):
    """Pull and optionally push. Auto-stashes dirty tree, handles forks.

    Examples:
      rudra git sync               # pull (rebase)
      rudra git sync --push        # pull then push
      rudra git sync --upstream    # fork workflow: pull upstream → push origin
      rudra git sync --force       # pull then force-push-with-lease
    """
    require_repo()
    cur = branch or current_branch()
    stashed = False

    if not is_clean():
        if stash:
            console.print("[yellow]Working tree dirty — stashing...[/yellow]")
            run(["git", "stash", "push", "-m", "rudra sync auto-stash"], "Stashing")
            stashed = True
        else:
            console.print("[yellow]Warning: working tree is dirty.[/yellow]")

    if upstream and has_remote("upstream"):
        default = default_branch()
        console.print(f"[dim]Pulling upstream/{default}...[/dim]")
        run(["git", "fetch", "upstream"], "Fetching upstream")
        run(["git", "checkout", default], f"Switching to {default}")
        run(["git", "merge", "--ff-only", f"upstream/{default}"], f"Merging upstream/{default}")
        run(["git", "push", remote, default], f"Pushing {default} to {remote}")
        if cur != default:
            run(["git", "checkout", cur], f"Back to {cur}")
        console.print(f"[bold green]✓ Synced {default} from upstream.[/bold green]")

    pull_args = ["git", "pull", "--rebase" if rebase else "--no-rebase", remote, cur]
    run(pull_args, f"Pulling {remote}/{cur}")

    if push or force_push:
        push_args = ["git", "push", remote, cur]
        if force_push:
            push_args.insert(2, "--force-with-lease")
        run(push_args, f"Pushing {cur} → {remote}")

    if stashed:
        run(["git", "stash", "pop"], "Restoring stashed changes")

    ahead, behind = ahead_behind(cur)
    sha = short_hash()
    console.print(f"\n[bold green]✓ Synced.[/bold green]  [dim]{sha}[/dim]", end="")
    if ahead:
        console.print(f"  [green]↑{ahead}[/green]", end="")
    if behind:
        console.print(f"  [red]↓{behind}[/red]", end="")
    console.print()


@app.command()
def push(
    branch: Annotated[Optional[str], typer.Argument(help="Branch to push.")] = None,
    remote: Annotated[str, typer.Option("--remote", help="Remote to push to.")] = "origin",
    force: Annotated[bool, typer.Option("--force", "-f", help="Force push with lease.")] = False,
    tags: Annotated[bool, typer.Option("--tags", help="Also push tags.")] = False,
):
    """Push the current branch to remote.

    Examples:
      rudra git push
      rudra git push --force    # safe force push (--force-with-lease)
      rudra git push --tags
    """
    require_repo()
    cur = branch or current_branch()
    args = ["git", "push", "-u"]
    if force:
        args.append("--force-with-lease")
    if tags:
        args.append("--follow-tags")
    args += [remote, cur]
    run(args, f"Pushing {cur} → {remote}")
    console.print(f"[bold green]✓ Pushed {cur} → {remote}.[/bold green]")


@app.command()
def pull(
    branch: Annotated[Optional[str], typer.Argument(help="Branch to pull.")] = None,
    remote: Annotated[str, typer.Option("--remote", help="Remote to pull from.")] = "origin",
    rebase: Annotated[bool, typer.Option("--rebase/--merge", help="Rebase or merge.")] = True,
):
    """Pull the current branch from remote."""
    require_repo()
    cur = branch or current_branch()
    args = ["git", "pull", "--rebase" if rebase else "--no-rebase", remote, cur]
    run(args, f"Pulling {remote}/{cur}")
    console.print(f"[bold green]✓ Pulled {remote}/{cur}.[/bold green]")
