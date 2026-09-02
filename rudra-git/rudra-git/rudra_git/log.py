"""rudra git log — pretty log, graph, file history."""

from __future__ import annotations
from typing import Annotated, Optional
import typer
from rich.console import Console
from rich.table import Table
from rudra_git.helpers import git, require_repo

app = typer.Typer()
console = Console()


@app.command()
def log(
    n: Annotated[int, typer.Option("--count", "-n", help="Number of commits.")] = 15,
    file: Annotated[Optional[str], typer.Option("--file", "-f", help="Filter to a specific file.")] = None,
    author: Annotated[Optional[str], typer.Option("--author", "-a", help="Filter by author.")] = None,
    grep: Annotated[Optional[str], typer.Option("--grep", "-g", help="Filter by commit message.")] = None,
    since: Annotated[Optional[str], typer.Option("--since", help="E.g. '2 weeks ago'.")] = None,
    graph: Annotated[bool, typer.Option("--graph", help="Show branch graph.")] = False,
    stat: Annotated[bool, typer.Option("--stat", help="Show file stats per commit.")] = False,
    patch: Annotated[bool, typer.Option("--patch", "-p", help="Show full diff.")] = False,
    oneline: Annotated[bool, typer.Option("--oneline", help="Compact one-line format.")] = False,
):
    """Pretty commit history — table, graph, or diff view.

    Examples:
      rudra git log
      rudra git log --graph
      rudra git log --file src/main.py
      rudra git log --author "Abhinav" --since "1 week ago"
      rudra git log --grep "fix" --patch
    """
    require_repo()

    if graph:
        code, out = git(
            "log", f"-{n}", "--graph",
            "--pretty=format:%C(yellow)%h%Creset %C(cyan)%d%Creset %s %C(dim)(%cr) <%an>%Creset",
            "--abbrev-commit", "--decorate",
        )
        if code == 0:
            console.print(out)
        return

    if patch or stat:
        args = ["log", f"-{n}", "--color=always"]
        if patch:
            args.append("-p")
        if stat:
            args.append("--stat")
        if author:
            args.append(f"--author={author}")
        if grep:
            args.append(f"--grep={grep}")
        if since:
            args.append(f"--since={since}")
        if file:
            args += ["--", file]
        code, out = git(*args)
        if code == 0:
            console.print(out)
        return

    if oneline:
        args = ["log", f"-{n}", "--oneline", "--decorate"]
        if author:
            args.append(f"--author={author}")
        if grep:
            args.append(f"--grep={grep}")
        if since:
            args.append(f"--since={since}")
        if file:
            args += ["--", file]
        code, out = git(*args)
        if code == 0:
            console.print(out)
        return

    # Rich table
    fmt = "%H\t%h\t%an\t%ar\t%s\t%D"
    args = ["log", f"-{n}", f"--pretty=format:{fmt}"]
    if author:
        args.append(f"--author={author}")
    if grep:
        args.append(f"--grep={grep}")
    if since:
        args.append(f"--since={since}")
    if file:
        args += ["--", file]

    code, out = git(*args)
    if code != 0 or not out.strip():
        console.print("[dim]No commits found.[/dim]")
        return

    table = Table(show_header=True, header_style="bold dim", box=None, padding=(0, 1))
    table.add_column("hash", style="yellow", no_wrap=True)
    table.add_column("author", style="cyan", no_wrap=True)
    table.add_column("when", style="dim", no_wrap=True)
    table.add_column("message")
    table.add_column("refs", style="dim")

    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) < 6:
            continue
        _, short, author_n, when, msg, refs = parts[:6]
        if len(msg) > 72:
            msg = msg[:69] + "…"
        table.add_row(short, author_n, when, msg, refs)

    console.print()
    console.print(table)
    console.print()


@app.command(name="file-log")
def file_log(
    path: Annotated[str, typer.Argument(help="File to show history for.")],
    n: Annotated[int, typer.Option("--count", "-n")] = 20,
    patch: Annotated[bool, typer.Option("--patch", "-p", help="Show diff per commit.")] = False,
):
    """Show commit history for a file, including renames.

    Examples:
      rudra git file-log src/main.py
      rudra git file-log src/main.py --patch
    """
    require_repo()
    args = ["log", f"-{n}", "--follow", "-p" if patch else "--oneline", "--", path]
    code, out = git(*args)
    if code != 0 or not out.strip():
        console.print(f"[dim]No history for '{path}'.[/dim]")
        return
    console.print(f"[bold dim]History for {path}:[/bold dim]\n")
    if patch:
        console.print(out)
    else:
        for line in out.splitlines():
            parts = line.split(" ", 1)
            if len(parts) == 2:
                console.print(f"  [yellow]{parts[0]}[/yellow]  {parts[1]}")
    console.print()
