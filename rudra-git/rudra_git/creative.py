"""rudra-git creative superpowers: panic, graph, blame-game."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()
app = typer.Typer(help="Creative & power-user git commands.", no_args_is_help=False)


# ── helpers ───────────────────────────────────────────────────────────────────

def _git(*args: str) -> tuple[int, str]:
    r = subprocess.run(["git", *args], capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


def _in_repo() -> bool:
    code, _ = _git("rev-parse", "--is-inside-work-tree")
    return code == 0


# ── rudra git panic ────────────────────────────────────────────────────────────

@app.command(name="panic")
def panic(
    msg: str = typer.Option("WIP: stashing before the boss arrives", "--msg", "-m",
                             help="Stash message to attach."),
):
    """🚨 BOSS MODE — stash everything, switch to a clean branch, nuke the screen.

    Instantly hides all your dirty work so you look like you're on a meeting dashboard.

    Example:
      rudra git panic
      rudra git panic --msg "hide experimental feature"
    """
    if not _in_repo():
        console.print("[bold red]Not inside a git repo.[/bold red]")
        raise typer.Exit(1)

    # 1. Stash everything including untracked
    console.print("[bold yellow]🚨 Rudra Panic Mode activated...[/bold yellow]")
    code, out = _git("stash", "push", "-u", "-m", msg)
    if code != 0 and "No local changes" not in out:
        console.print(f"[dim]Stash note: {out}[/dim]")

    # 2. Get or create a dummy "cover" branch
    _, current = _git("branch", "--show-current")
    _, branches = _git("branch")
    branch_list = [b.strip().lstrip("* ") for b in branches.splitlines()]
    cover_branch = "docs/readme-updates"
    if cover_branch not in branch_list:
        _git("checkout", "-b", cover_branch)
    else:
        _git("checkout", cover_branch)

    # 3. Wipe terminal
    os.system("clear" if sys.platform != "win32" else "cls")

    console.print(Panel(
        "[bold green]✓ All changes stashed safely.[/bold green]\n"
        f"[dim]Stash message:[/dim] [italic]{msg}[/italic]\n"
        f"[dim]Switched branch:[/dim] [cyan]{current}[/cyan] → [cyan]{cover_branch}[/cyan]\n\n"
        "[dim]To restore your work after the boss leaves:[/dim]\n"
        f"  [bold cyan]git checkout {current}[/bold cyan]\n"
        "  [bold cyan]git stash pop[/bold cyan]",
        title="[bold yellow]🛡  Panic Mode — You are safe[/bold yellow]",
        border_style="yellow",
    ))


# ── rudra git graph ────────────────────────────────────────────────────────────

@app.command(name="graph")
def graph(
    n: int = typer.Option(30, "--count", "-n", help="Number of commits to show."),
    all_branches: bool = typer.Option(True, "--all/--current", help="Show all branches (default) or just current branch."),
):
    """🌳 Show a beautiful coloured ASCII git commit tree.

    Examples:
      rudra git graph
      rudra git graph --count 50
      rudra git graph --current
    """
    if not _in_repo():
        console.print("[bold red]Not inside a git repo.[/bold red]")
        raise typer.Exit(1)

    args = ["log", f"-{n}",
            "--graph",
            "--pretty=format:%C(bold yellow)%h%Creset %C(cyan)(%ar)%Creset %C(bold white)%s%Creset %C(dim)— %an%Creset",
            "--abbrev-commit", "--date=relative"]
    if all_branches:
        args.append("--all")

    code, out = _git(*args)
    if code != 0 or not out:
        console.print("[yellow]Nothing to graph yet — no commits found.[/yellow]")
        raise typer.Exit(0)

    console.print(Panel.fit("[bold cyan]🌳 Git Repository Commit Graph[/bold cyan]", border_style="cyan"))
    # Wrap output in Rich markup: just print as plain since git uses ANSI codes
    import sys
    subprocess.run(["git", "log", f"-{n}", "--graph",
        "--pretty=format:%C(bold yellow)%h%Creset %C(cyan)(%ar)%Creset %C(bold white)%s%Creset %C(dim)— %an%Creset",
        "--abbrev-commit", "--date=relative"] + (["--all"] if all_branches else []),
        env={**os.environ, "GIT_PAGER": "cat"})


# ── rudra git blame-game ───────────────────────────────────────────────────────

@app.command(name="blame-game")
def blame_game(
    n: int = typer.Option(500, "--commits", "-n", help="Number of recent commits to scan."),
):
    """🏆 Hall of fame — who wrote the most lines, commits, and night-owl sessions?

    Shows contributor leaderboard: commit count, insertions, deletions,
    and who's been coding past midnight.

    Example:
      rudra git blame-game
      rudra git blame-game --commits 200
    """
    if not _in_repo():
        console.print("[bold red]Not inside a git repo.[/bold red]")
        raise typer.Exit(1)

    console.print(Panel.fit("[bold cyan]🏆 Git Blame Game — Contributor Leaderboard[/bold cyan]", border_style="cyan"))

    # Get log with author + numstat
    code, log_out = _git("log", f"-{n}", "--pretty=format:COMMIT|%an|%ae|%ad", "--date=format:%H",
                          "--numstat")
    if code != 0 or not log_out:
        console.print("[yellow]No commits to analyze.[/yellow]")
        raise typer.Exit(0)

    stats: dict[str, dict] = {}
    current_author = None
    current_hour: Optional[int] = None

    for line in log_out.splitlines():
        if line.startswith("COMMIT|"):
            parts = line.split("|")
            current_author = parts[1] if len(parts) > 1 else "Unknown"
            current_hour   = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else None
            if current_author not in stats:
                stats[current_author] = {"commits": 0, "added": 0, "deleted": 0, "night_sessions": 0}
            stats[current_author]["commits"] += 1
            if current_hour is not None and (current_hour >= 22 or current_hour < 4):
                stats[current_author]["night_sessions"] += 1
        elif line and current_author:
            parts = line.split("\t")
            if len(parts) == 3:
                try:
                    stats[current_author]["added"]   += int(parts[0])
                    stats[current_author]["deleted"]  += int(parts[1])
                except ValueError:
                    pass  # Binary file rows contain '-'

    if not stats:
        console.print("[yellow]No contributor data found.[/yellow]")
        return

    sorted_authors = sorted(stats.items(), key=lambda x: x[1]["commits"], reverse=True)

    table = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 2))
    table.add_column("Rank", style="bold yellow", width=6)
    table.add_column("Author", style="bold white", min_width=18)
    table.add_column("Commits", justify="right", style="green")
    table.add_column("Lines Added", justify="right", style="cyan")
    table.add_column("Lines Deleted", justify="right", style="red")
    table.add_column("🌙 Night Commits", justify="right", style="dim magenta")

    medals = ["🥇", "🥈", "🥉"]
    for i, (author, s) in enumerate(sorted_authors):
        medal = medals[i] if i < 3 else f"#{i+1}"
        table.add_row(
            medal, author,
            str(s["commits"]),
            f"+{s['added']}",
            f"-{s['deleted']}",
            str(s["night_sessions"]) if s["night_sessions"] > 0 else "[dim]—[/dim]",
        )

    console.print(table)

    # Fun facts
    top_author, top_stats = sorted_authors[0]
    top_night = max(stats.items(), key=lambda x: x[1]["night_sessions"])
    console.print(f"\n[bold green]👑 Top Contributor:[/bold green] {top_author} with {top_stats['commits']} commits")
    if top_night[1]["night_sessions"] > 0:
        console.print(f"[bold magenta]🌙 Night Owl Award:[/bold magenta] {top_night[0]} — {top_night[1]['night_sessions']} commits past 10pm")
    console.print()
