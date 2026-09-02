"""rudra git commit — smart commit, amend, fixup, conventional commits."""

from __future__ import annotations
from typing import Annotated, Optional
import typer
from rich.console import Console
from rudra_git.helpers import git, run, require_repo, short_hash, current_branch

app = typer.Typer()
console = Console()

_CONV_TYPES = [
    ("feat",     "A new feature"),
    ("fix",      "A bug fix"),
    ("docs",     "Documentation only"),
    ("style",    "Formatting, no logic change"),
    ("refactor", "Code change, not feat or fix"),
    ("perf",     "Performance improvement"),
    ("test",     "Adding/fixing tests"),
    ("chore",    "Build, tooling, deps"),
    ("ci",       "CI/CD changes"),
    ("revert",   "Revert a previous commit"),
]


def _pick_conv_type() -> str:
    console.print("\n[bold]Commit type:[/bold]")
    for i, (t, desc) in enumerate(_CONV_TYPES, 1):
        console.print(f"  [cyan]{i:2}[/cyan]  [bold]{t:<10}[/bold] [dim]{desc}[/dim]")
    raw = typer.prompt("Type", default="1").strip()
    try:
        idx = int(raw) - 1
        if 0 <= idx < len(_CONV_TYPES):
            return _CONV_TYPES[idx][0]
    except ValueError:
        if raw in {t for t, _ in _CONV_TYPES}:
            return raw
    return _CONV_TYPES[0][0]


def _staged_files() -> list[str]:
    code, out = git("diff", "--cached", "--name-only")
    return out.strip().splitlines() if code == 0 and out.strip() else []


def _ensure_staged() -> bool:
    """Make sure something is staged. Returns False if user aborts."""
    staged = _staged_files()
    if staged:
        return True
    code, out = git("status", "--porcelain")
    if code == 0 and out.strip():
        console.print("[yellow]Nothing staged.[/yellow]  Unstaged changes detected.")
        if typer.confirm("Stage everything and commit?", default=True):
            run(["git", "add", "-A"], "Staging all changes")
            return True
    else:
        console.print("[dim]Nothing to commit, working tree clean.[/dim]")
    return False


@app.command()
def commit(
    message: Annotated[Optional[str], typer.Argument(help="Commit message. Omit to be prompted.")] = None,
    all_: Annotated[bool, typer.Option("--all", "-a", help="Stage all tracked changes first.")] = False,
    conventional: Annotated[bool, typer.Option("--conv", "-c", help="Interactive conventional commit builder.")] = False,
    amend: Annotated[bool, typer.Option("--amend", help="Amend the last commit.")] = False,
    no_edit: Annotated[bool, typer.Option("--no-edit", help="Amend without changing the message.")] = False,
    push: Annotated[bool, typer.Option("--push", "-p", help="Push after committing.")] = False,
    empty: Annotated[bool, typer.Option("--empty", help="Allow empty commit (useful for triggering CI).")] = False,
):
    """Stage and commit — with conventional commit builder and smart staging.

    Examples:
      rudra git commit "fix login bug"
      rudra git commit -a "fix login bug"   # stage all tracked + commit
      rudra git commit --conv               # interactive conventional commit
      rudra git commit --amend --no-edit    # amend without editing message
      rudra git commit "wip" --push         # commit + push in one shot
    """
    require_repo()

    if amend:
        args = ["git", "commit", "--amend"]
        if all_:
            args.append("-a")
        if no_edit:
            args.append("--no-edit")
        run(args, "Amending last commit")
        console.print(f"[bold green]✓ Amended.[/bold green]  [dim]{short_hash()}[/dim]")
        if push:
            run(["git", "push", "--force-with-lease"], "Force-pushing amended commit")
        return

    if all_:
        run(["git", "add", "-u"], "Staging all tracked changes")

    if not empty and not _ensure_staged():
        raise typer.Exit(0)

    staged = _staged_files()
    if staged:
        preview = ", ".join(staged[:5]) + (" …" if len(staged) > 5 else "")
        console.print(f"[dim]Staging {len(staged)} file(s): {preview}[/dim]")

    if conventional:
        conv_type = _pick_conv_type()
        scope = typer.prompt("Scope (optional, enter to skip)", default="").strip()
        summary = typer.prompt("Summary").strip()
        breaking = typer.confirm("Breaking change?", default=False)
        body = typer.prompt("Body (optional)", default="").strip()
        scope_part = f"({scope})" if scope else ""
        breaking_mark = "!" if breaking else ""
        message = f"{conv_type}{scope_part}{breaking_mark}: {summary}"
        if body:
            message += f"\n\n{body}"
        if breaking:
            message += f"\n\nBREAKING CHANGE: {summary}"
    elif message is None:
        message = typer.prompt("Commit message").strip()
        if not message:
            console.print("[red]Empty message — aborting.[/red]")
            raise typer.Exit(1)

    args = ["git", "commit", "-m", message]
    if empty:
        args.append("--allow-empty")
    run(args, "Committing")
    console.print(f"[bold green]✓[/bold green]  [dim]{short_hash()}[/dim]  {message.splitlines()[0][:72]}")

    if push:
        branch = current_branch()
        run(["git", "push", "-u", "origin", branch], f"Pushing {branch}")


@app.command()
def fixup(
    target: Annotated[Optional[str], typer.Argument(help="Commit to fix up. Omit to pick from log.")] = None,
    rebase: Annotated[bool, typer.Option("--rebase", "-r", help="Autosquash immediately after.")] = False,
):
    """Create a fixup commit for a previous commit, then optionally autosquash.

    Examples:
      rudra git fixup abc1234
      rudra git fixup --rebase   # pick from log + autosquash
    """
    require_repo()

    if target is None:
        code, out = git("log", "--oneline", "-10")
        if code != 0:
            console.print("[red]Could not read git log.[/red]")
            raise typer.Exit(1)
        lines = out.splitlines()
        console.print("\n[bold]Pick a commit to fixup:[/bold]")
        for i, line in enumerate(lines, 1):
            parts = line.split(" ", 1)
            console.print(f"  [cyan]{i}[/cyan]  [yellow]{parts[0]}[/yellow]  {parts[1] if len(parts)>1 else ''}")
        raw = typer.prompt("Choice", default="1").strip()
        try:
            idx = int(raw) - 1
            target = lines[idx].split()[0]
        except (ValueError, IndexError):
            console.print("[red]Invalid choice.[/red]")
            raise typer.Exit(1)

    if not _staged_files():
        code, out = git("status", "--porcelain")
        if code == 0 and out.strip():
            if typer.confirm("Nothing staged. Stage everything?", default=True):
                run(["git", "add", "-A"], "Staging all changes")
            else:
                raise typer.Exit(0)

    run(["git", "commit", "--fixup", target], f"Creating fixup for {target}")
    console.print(f"[bold green]✓ Fixup created for {target}.[/bold green]")

    if rebase:
        run(["git", "rebase", "-i", "--autosquash", f"{target}^"], "Autosquashing")
        console.print("[bold green]✓ Autosquash complete.[/bold green]")
    else:
        console.print(f"[dim]Run [bold]rudra git fixup {target} --rebase[/bold] to autosquash.[/dim]")
