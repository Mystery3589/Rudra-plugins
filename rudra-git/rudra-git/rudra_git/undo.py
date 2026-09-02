"""rudra git undo / restore / reset."""

from __future__ import annotations
from typing import Annotated, Optional
import typer
from rich.console import Console
from rudra_git.helpers import run, require_repo, short_hash

app = typer.Typer()
console = Console()


@app.command()
def undo(
    n: Annotated[int, typer.Argument(help="Number of commits to undo.")] = 1,
    hard: Annotated[bool, typer.Option("--hard", help="Discard changes (destructive).")] = False,
    push: Annotated[bool, typer.Option("--push", "-p", help="Force-push after hard undo.")] = False,
):
    """Undo the last N commits. Keeps changes staged by default.

    Examples:
      rudra git undo              # undo last commit, keep staged
      rudra git undo 3            # undo 3 commits, keep staged
      rudra git undo --hard       # discard everything (destructive)
    """
    require_repo()
    mode = "--hard" if hard else "--soft"
    if hard:
        console.print(f"[bold red]⚠ Hard reset — {n} commit(s) and all changes will be discarded.[/bold red]")
        if not typer.confirm("Are you sure?", default=False):
            raise typer.Exit(0)
    run(["git", "reset", mode, f"HEAD~{n}"], f"Undoing {n} commit(s) ({mode})")
    console.print(f"[bold green]✓ Undid {n} commit(s).[/bold green]  [dim]{short_hash()}[/dim]")
    if push and hard:
        run(["git", "push", "--force-with-lease"], "Force-pushing")
    elif push:
        console.print("[yellow]--push only applies with --hard.[/yellow]")


@app.command()
def restore(
    paths: Annotated[Optional[list[str]], typer.Argument(help="File(s) to restore. Omit = restore all.")] = None,
    staged: Annotated[bool, typer.Option("--staged", "-s", help="Unstage (keep working tree changes).")] = False,
    source: Annotated[Optional[str], typer.Option("--from", help="Restore from a specific commit.")] = None,
):
    """Restore files — discard changes or unstage.

    Examples:
      rudra git restore src/main.py          # discard local changes
      rudra git restore --staged src/main.py # unstage
      rudra git restore                      # restore ALL modified files
      rudra git restore --from HEAD~2 file   # restore from 2 commits ago
    """
    require_repo()
    target = paths or ["."]

    if source:
        for p in target:
            run(["git", "checkout", source, "--", p], f"Restoring {p} from {source}")
        console.print(f"[bold green]✓ Restored from {source}.[/bold green]")
        return

    if staged:
        run(["git", "restore", "--staged"] + target, "Unstaging")
        console.print(f"[bold green]✓ Unstaged {', '.join(target)}.[/bold green]")
    else:
        if target == ["."]:
            console.print("[bold yellow]⚠ This will discard ALL uncommitted changes.[/bold yellow]")
            if not typer.confirm("Continue?", default=False):
                raise typer.Exit(0)
        run(["git", "restore"] + target, f"Restoring {', '.join(target)}")
        console.print("[bold green]✓ Restored.[/bold green]")


@app.command()
def reset(
    ref: Annotated[str, typer.Argument(help="Commit to reset to (HEAD~1, abc123, main).")],
    hard: Annotated[bool, typer.Option("--hard", help="Discard all changes.")] = False,
    soft: Annotated[bool, typer.Option("--soft", help="Keep changes staged.")] = False,
):
    """Reset HEAD to a specific commit.

    Examples:
      rudra git reset HEAD~2           # mixed (unstage changes)
      rudra git reset HEAD~1 --soft    # keep staged
      rudra git reset abc123 --hard    # discard everything
    """
    require_repo()
    if hard:
        mode = "--hard"
        console.print(f"[bold red]⚠ Hard reset to {ref} — all changes discarded.[/bold red]")
        if not typer.confirm("Are you sure?", default=False):
            raise typer.Exit(0)
    elif soft:
        mode = "--soft"
    else:
        mode = "--mixed"
    run(["git", "reset", mode, ref], f"Resetting to {ref} ({mode})")
    console.print(f"[bold green]✓ Reset to {ref}.[/bold green]  [dim]{short_hash()}[/dim]")
