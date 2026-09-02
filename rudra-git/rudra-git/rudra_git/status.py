"""rudra git status / info — pretty repo overview."""

from __future__ import annotations
from typing import Annotated
import typer
from rich.panel import Panel
from rich.table import Table
from rudra_git.helpers import (
    ahead_behind, all_branches, current_branch, git, is_clean,
    require_repo, short_hash, stash_list,
)

app = typer.Typer()


def _staged_unstaged_untracked():
    from rich.console import Console
    code, out = git("status", "--porcelain=v1")
    staged, unstaged, untracked = [], [], []
    if code != 0:
        return staged, unstaged, untracked
    for line in out.splitlines():
        if len(line) < 3:
            continue
        x, y, path = line[0], line[1], line[3:]
        if x not in (" ", "?"):
            staged.append(f"{x} {path}")
        if y not in (" ", "?"):
            unstaged.append(f"{y} {path}")
        if x == "?" and y == "?":
            untracked.append(path)
    return staged, unstaged, untracked


@app.command()
def status(
    short: Annotated[bool, typer.Option("--short", "-s", help="One-line summary only.")] = False,
):
    """Rich colour-coded repo status — staged, unstaged, untracked, stashes, sync."""
    from rich.console import Console
    console = Console()
    require_repo()

    branch = current_branch()
    sha = short_hash()
    ahead, behind = ahead_behind(branch)
    staged, unstaged, untracked = _staged_unstaged_untracked()
    stashes = stash_list()

    sync = ""
    if ahead and behind:
        sync = f" [yellow]↑{ahead} ↓{behind}[/yellow]"
    elif ahead:
        sync = f" [green]↑{ahead}[/green]"
    elif behind:
        sync = f" [red]↓{behind}[/red]"

    clean_label = "[green]clean[/green]" if is_clean() else "[yellow]dirty[/yellow]"
    stash_label = f"  [dim]{len(stashes)} stash(es)[/dim]" if stashes else ""
    console.print(f"[bold cyan]{branch}[/bold cyan] [dim]{sha}[/dim]{sync}  {clean_label}{stash_label}")

    if short:
        return

    if staged:
        console.print("\n[bold green]Staged:[/bold green]")
        for f in staged:
            console.print(f"  [green]{f}[/green]")
    if unstaged:
        console.print("\n[bold yellow]Unstaged:[/bold yellow]")
        for f in unstaged:
            console.print(f"  [yellow]{f}[/yellow]")
    if untracked:
        console.print("\n[bold dim]Untracked:[/bold dim]")
        for f in untracked:
            console.print(f"  [dim]{f}[/dim]")
    if stashes:
        console.print("\n[bold]Stashes:[/bold]")
        for ref, msg in stashes:
            console.print(f"  [cyan]{ref}[/cyan]  {msg}")
    if behind:
        console.print(f"\n[yellow]  ↓ {behind} commit(s) behind — run [bold]rudra git sync[/bold][/yellow]")
    if ahead:
        console.print(f"\n[green]  ↑ {ahead} commit(s) ahead — run [bold]rudra git sync --push[/bold][/green]")
    if not staged and not unstaged and not untracked:
        console.print("\n[dim]Nothing to commit, working tree clean.[/dim]")
    console.print()


@app.command()
def info():
    """Full repo dashboard — branches, remotes, recent commits, stashes."""
    from rich.console import Console
    console = Console()
    require_repo()

    branch = current_branch()
    sha = short_hash()
    branches = all_branches()
    branch_text = "  ".join(
        f"[bold cyan]{b}[/bold cyan]" if b == branch else f"[dim]{b}[/dim]"
        for b in branches[:12]
    )
    if len(branches) > 12:
        branch_text += f" [dim]+{len(branches)-12} more[/dim]"

    code, remotes_raw = git("remote", "-v")
    remote_lines, seen = [], set()
    for line in (remotes_raw or "").splitlines():
        if "(fetch)" in line:
            parts = line.split()
            if len(parts) >= 2 and parts[0] not in seen:
                seen.add(parts[0])
                remote_lines.append(f"  [cyan]{parts[0]}[/cyan]  {parts[1]}")

    code, log_raw = git("log", "--oneline", "-8", "--decorate")
    log_lines = log_raw.splitlines() if code == 0 else []
    stashes = stash_list()

    table = Table(box=None, show_header=False, padding=(0, 2))
    table.add_column(style="bold dim", no_wrap=True)
    table.add_column()
    table.add_row("branch", f"[bold cyan]{branch}[/bold cyan]  [dim]{sha}[/dim]")
    table.add_row("branches", branch_text or "[dim]none[/dim]")
    table.add_row("remotes", "\n".join(remote_lines) if remote_lines else "[dim]none[/dim]")
    table.add_row("stashes", str(len(stashes)) if stashes else "[dim]0[/dim]")
    console.print(Panel(table, title="[bold]repo info[/bold]", border_style="cyan"))

    if log_lines:
        console.print("[bold dim]Recent commits:[/bold dim]")
        for line in log_lines:
            parts = line.split(" ", 1)
            if len(parts) == 2:
                console.print(f"  [yellow]{parts[0]}[/yellow]  {parts[1]}")
        console.print()
