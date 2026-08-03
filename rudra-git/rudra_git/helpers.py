"""Shared git plumbing helpers used across all rudra-git submodules."""

from __future__ import annotations

import shutil
import subprocess
from typing import Optional

import typer
from rich.console import Console

console = Console()


def require_git() -> None:
    if not shutil.which("git"):
        console.print("[bold red]git is not installed or not on PATH.[/bold red]")
        raise typer.Exit(1)


def require_repo() -> None:
    require_git()
    code, _ = _capture(["git", "rev-parse", "--is-inside-work-tree"])
    if code != 0:
        console.print("[bold red]Not inside a git repository.[/bold red]")
        raise typer.Exit(1)


def _capture(cmd: list[str], timeout: float = 10) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return -1, ""
    except FileNotFoundError:
        return -1, ""


def git(*args: str) -> tuple[int, str]:
    return _capture(["git", *args])


def git_ok(*args: str) -> str:
    code, out = _capture(["git", *args])
    if code != 0:
        console.print(f"[bold red]git {' '.join(args)} failed:[/bold red]\n{out}")
        raise typer.Exit(1)
    return out.strip()


def run(cmd: list[str], description: str | None = None) -> None:
    if description:
        console.print(f"[bold cyan]==> {description}[/bold cyan]")
    console.print(f"[dim]$ {' '.join(cmd)}[/dim]")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        console.print(f"[bold red]Command failed (exit {result.returncode})[/bold red]")
        raise typer.Exit(result.returncode)


def current_branch() -> str:
    code, out = git("rev-parse", "--abbrev-ref", "HEAD")
    return out.strip() if code == 0 else "HEAD"


def default_branch() -> str:
    code, out = git("rev-parse", "--abbrev-ref", "origin/HEAD")
    if code == 0 and "/" in out:
        return out.strip().split("/", 1)[1]
    for candidate in ("main", "master", "develop"):
        code, _ = git("show-ref", "--verify", "--quiet", f"refs/heads/{candidate}")
        if code == 0:
            return candidate
    return "main"


def is_clean() -> bool:
    code, out = git("status", "--porcelain")
    return code == 0 and out.strip() == ""


def has_remote(name: str = "origin") -> bool:
    code, _ = git("remote", "get-url", name)
    return code == 0


def all_branches(include_remote: bool = False) -> list[str]:
    args = ["branch", "--format=%(refname:short)"]
    if include_remote:
        args.append("-a")
    code, out = git(*args)
    if code != 0:
        return []
    return [b.strip().lstrip("* ") for b in out.splitlines() if b.strip()]


def stash_list() -> list[tuple[str, str]]:
    code, out = git("stash", "list", "--format=%gd\t%s")
    if code != 0 or not out.strip():
        return []
    entries = []
    for line in out.splitlines():
        parts = line.split("\t", 1)
        if len(parts) == 2:
            entries.append((parts[0], parts[1]))
    return entries


def short_hash(ref: str = "HEAD") -> str:
    code, out = git("rev-parse", "--short", ref)
    return out.strip() if code == 0 else "?"


def ahead_behind(branch: str, upstream: Optional[str] = None) -> tuple[int, int]:
    if upstream is None:
        code, out = git("rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}")
        if code != 0:
            return 0, 0
        upstream = out.strip()
    code, out = git("rev-list", "--left-right", "--count", f"{upstream}...{branch}")
    if code != 0 or not out.strip():
        return 0, 0
    parts = out.strip().split()
    if len(parts) == 2:
        return int(parts[1]), int(parts[0])
    return 0, 0
