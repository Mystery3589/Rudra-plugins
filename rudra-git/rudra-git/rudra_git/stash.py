"""rudra git stash — push, pop, apply, list, drop."""

from __future__ import annotations
from typing import Annotated, Optional
import typer
from rich.console import Console
from rudra_git.helpers import run, require_repo, stash_list

app = typer.Typer()
console = Console()


def _pick_stash(stashes: list[tuple[str, str]], prompt: str = "Which stash?") -> str:
    console.print("\n[bold]Stashes:[/bold]")
    for i, (ref, msg) in enumerate(stashes, 1):
        console.print(f"  [cyan]{i}[/cyan]  [dim]{ref}[/dim]  {msg}")
    raw = typer.prompt(prompt, default="1").strip()
    try:
        idx = int(raw) - 1
        if 0 <= idx < len(stashes):
            return stashes[idx][0]
    except ValueError:
        if raw.startswith("stash@"):
            return raw
    console.print("[yellow]Invalid, using stash@{0}.[/yellow]")
    return "stash@{0}"


@app.command(name="stash")
def stash_push(
    message: Annotated[Optional[str], typer.Argument(help="Stash name/message.")] = None,
    untracked: Annotated[bool, typer.Option("--untracked", "-u", help="Include untracked files.")] = False,
    keep_index: Annotated[bool, typer.Option("--keep-index", help="Keep staged changes in index.")] = False,
    patch: Annotated[bool, typer.Option("--patch", "-p", help="Interactively pick hunks.")] = False,
):
    """Save current changes to the stash stack."""
    require_repo()
    args = ["git", "stash", "push"]
    if untracked:
        args.append("--include-untracked")
    if keep_index:
        args.append("--keep-index")
    if patch:
        args.append("--patch")
    if message:
        args += ["-m", message]
    run(args, "Stashing changes")
    stashes = stash_list()
    console.print(f"[bold green]✓ Stashed.[/bold green]" + (f"  [dim]{stashes[0][1]}[/dim]" if stashes else ""))


@app.command(name="stash-pop")
def stash_pop(
    index: Annotated[Optional[int], typer.Argument(help="Stash number (1-based).")] = None,
):
    """Pop and apply a stash. Prompts if multiple stashes exist."""
    require_repo()
    stashes = stash_list()
    if not stashes:
        console.print("[dim]No stashes.[/dim]")
        raise typer.Exit(0)
    if index is not None:
        ref = stashes[index - 1][0] if 1 <= index <= len(stashes) else "stash@{0}"
    elif len(stashes) == 1:
        ref = "stash@{0}"
    else:
        ref = _pick_stash(stashes, "Which stash to pop?")
    run(["git", "stash", "pop", ref], f"Popping {ref}")
    console.print(f"[bold green]✓ Popped {ref}.[/bold green]")


@app.command(name="stash-apply")
def stash_apply(
    index: Annotated[Optional[int], typer.Argument(help="Stash number (1-based).")] = None,
):
    """Apply a stash without removing it from the stack."""
    require_repo()
    stashes = stash_list()
    if not stashes:
        console.print("[dim]No stashes.[/dim]")
        raise typer.Exit(0)
    if index is not None:
        ref = stashes[index - 1][0] if 1 <= index <= len(stashes) else "stash@{0}"
    elif len(stashes) == 1:
        ref = "stash@{0}"
    else:
        ref = _pick_stash(stashes, "Which stash to apply?")
    run(["git", "stash", "apply", ref], f"Applying {ref}")
    console.print(f"[bold green]✓ Applied {ref} (still in stack).[/bold green]")


@app.command(name="stash-list")
def stash_list_cmd():
    """List all stashes with index numbers."""
    require_repo()
    stashes = stash_list()
    if not stashes:
        console.print("[dim]No stashes.[/dim]")
        return
    console.print()
    for i, (ref, msg) in enumerate(stashes, 1):
        console.print(f"  [cyan]{i}[/cyan]  [dim]{ref}[/dim]  {msg}")
    console.print()


@app.command(name="stash-drop")
def stash_drop(
    index: Annotated[Optional[int], typer.Argument(help="Stash number (1-based).")] = None,
    all_: Annotated[bool, typer.Option("--all", "-a", help="Drop all stashes.")] = False,
):
    """Drop a stash or clear the entire stack."""
    require_repo()
    if all_:
        stashes = stash_list()
        if not stashes:
            console.print("[dim]No stashes.[/dim]")
            return
        if typer.confirm(f"Drop all {len(stashes)} stash(es)?", default=False):
            run(["git", "stash", "clear"], "Clearing all stashes")
            console.print("[bold green]✓ All stashes cleared.[/bold green]")
        return
    stashes = stash_list()
    if not stashes:
        console.print("[dim]No stashes.[/dim]")
        raise typer.Exit(0)
    if index is not None:
        ref = stashes[index - 1][0] if 1 <= index <= len(stashes) else "stash@{0}"
    elif len(stashes) == 1:
        ref = "stash@{0}"
    else:
        ref = _pick_stash(stashes, "Which stash to drop?")
    run(["git", "stash", "drop", ref], f"Dropping {ref}")
    console.print(f"[bold green]✓ Dropped {ref}.[/bold green]")
