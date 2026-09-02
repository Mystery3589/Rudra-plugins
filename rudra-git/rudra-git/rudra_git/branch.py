"""rudra git branch — create, switch, delete, clean merged."""

from __future__ import annotations
from typing import Annotated, Optional
import typer
from rich.console import Console
from rudra_git.helpers import (
    all_branches, current_branch, default_branch, git, run, require_repo,
)

app = typer.Typer()
console = Console()


@app.command()
def branch(
    name: Annotated[Optional[str], typer.Argument(help="Branch name. Omit to list.")] = None,
    switch: Annotated[bool, typer.Option("--switch/--no-switch", "-s", help="Switch after creating.")] = True,
    from_: Annotated[Optional[str], typer.Option("--from", help="Base branch or commit.")] = None,
    delete: Annotated[bool, typer.Option("--delete", "-d", help="Delete the branch.")] = False,
    force_delete: Annotated[bool, typer.Option("--force-delete", "-D", help="Force delete even if unmerged.")] = False,
    clean: Annotated[bool, typer.Option("--clean", help="Delete all merged branches.")] = False,
    remote: Annotated[bool, typer.Option("--remote", "-r", help="Include remote branches.")] = False,
):
    """Create, switch, delete, or list branches.

    Examples:
      rudra git branch                     # list
      rudra git branch feature/login       # create + switch
      rudra git branch feature/x --from main
      rudra git branch old -d              # delete merged
      rudra git branch --clean             # delete all merged
    """
    require_repo()

    if name is None and not clean:
        cur = current_branch()
        for b in all_branches(include_remote=remote):
            if b == cur:
                console.print(f"  [bold cyan]* {b}[/bold cyan]")
            else:
                console.print(f"    [dim]{b}[/dim]")
        return

    if clean:
        default = default_branch()
        cur = current_branch()
        if cur != default:
            run(["git", "checkout", default], f"Switching to {default}")
        code, out = git("branch", "--merged", default)
        if code != 0:
            console.print("[red]Could not list merged branches.[/red]")
            raise typer.Exit(1)
        to_delete = [
            b.strip().lstrip("* ")
            for b in out.splitlines()
            if b.strip().lstrip("* ") not in (default, "")
        ]
        if not to_delete:
            console.print("[dim]No merged branches to clean.[/dim]")
            return
        console.print("[yellow]Merged branches to delete:[/yellow]")
        for b in to_delete:
            console.print(f"  [dim]{b}[/dim]")
        if typer.confirm(f"\nDelete {len(to_delete)} branch(es)?", default=True):
            for b in to_delete:
                run(["git", "branch", "-d", b], f"Deleting {b}")
            console.print(f"[bold green]✓ Cleaned {len(to_delete)} branch(es).[/bold green]")
        return

    if delete or force_delete:
        run(["git", "branch", "-D" if force_delete else "-d", name], f"Deleting '{name}'")
        console.print(f"[bold green]✓ Deleted '{name}'.[/bold green]")
        return

    if name in all_branches():
        console.print(f"[dim]Branch '{name}' already exists.[/dim]")
        if switch:
            run(["git", "checkout", name], f"Switching to '{name}'")
            console.print(f"[bold cyan]→ {name}[/bold cyan]")
        return

    if switch:
        args = ["git", "checkout", "-b", name]
        if from_:
            args.append(from_)
        run(args, f"Creating + switching to '{name}'")
        console.print(f"[bold green]✓[/bold green] Created and switched to [bold cyan]{name}[/bold cyan]")
    else:
        args = ["git", "branch", name]
        if from_:
            args.append(from_)
        run(args, f"Creating '{name}'")
        console.print(f"[bold green]✓[/bold green] Created [bold cyan]{name}[/bold cyan]")
