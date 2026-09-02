"""rudra git extras — fun and automation commands.

  wip          Commit everything as WIP and push
  unwip        Undo the last WIP commit and restore working tree
  ship         sync → check → commit → push in one flow
  oops         Fix the last commit (forgotten file, typo in message)
  nuke         Delete a branch locally AND remotely
  yeet         Force push with dramatic confirmation
  panic        Something broke — interactive recovery menu
  contrib      Pretty contribution stats by author
  time-travel  Pick any commit and restore repo to that point
  changelog    Auto-generate a changelog from commits since last tag
"""

from __future__ import annotations
import subprocess
import shutil
from typing import Annotated, Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rudra_git.helpers import (
    all_branches, current_branch, default_branch, git,
    is_clean, require_repo, run, short_hash, stash_list,
)

app = typer.Typer()
console = Console()

_WIP_PREFIX = "WIP: 🚧 [rudra wip]"


# ── wip / unwip ───────────────────────────────────────────────────────────────

@app.command()
def wip(
    push: Annotated[bool, typer.Option("--push", "-p", help="Push the WIP commit after creating it.")] = False,
    message: Annotated[Optional[str], typer.Option("--message", "-m", help="Custom WIP message.")] = None,
):
    """Commit EVERYTHING as WIP so you can switch context fast.

    Run `rudra git unwip` when you're back to undo it cleanly.

    Examples:
      rudra git wip
      rudra git wip --push          # push to remote too
      rudra git wip -m "auth stuff" # custom label
    """
    require_repo()
    if is_clean():
        console.print("[dim]Nothing to stash — working tree is already clean.[/dim]")
        raise typer.Exit(0)

    msg = f"{_WIP_PREFIX} {message}" if message else f"{_WIP_PREFIX} {current_branch()}"
    run(["git", "add", "-A"], "Staging everything")
    run(["git", "commit", "-m", msg], "Creating WIP commit")
    console.print(f"[bold green]✓ WIP committed.[/bold green]  [dim]{short_hash()}[/dim]")
    console.print("[dim]Run [bold]rudra git unwip[/bold] when you're back.[/dim]")

    if push:
        run(["git", "push", "-u", "origin", current_branch()], "Pushing WIP")


@app.command()
def unwip():
    """Undo the last WIP commit and restore the working tree exactly as it was.

    Only works if the last commit was made by `rudra git wip`.
    """
    require_repo()
    code, msg = git("log", "-1", "--pretty=%s")
    if code != 0 or _WIP_PREFIX not in msg:
        console.print(f"[bold red]Last commit doesn't look like a rudra WIP commit:[/bold red]")
        console.print(f"  [dim]{msg.strip()}[/dim]")
        if not typer.confirm("Undo it anyway (soft reset)?", default=False):
            raise typer.Exit(0)
    run(["git", "reset", "HEAD~1"], "Undoing WIP commit (soft reset)")
    console.print("[bold green]✓ WIP undone.[/bold green] Your changes are back in the working tree.")


# ── ship ──────────────────────────────────────────────────────────────────────

@app.command()
def ship(
    message: Annotated[Optional[str], typer.Argument(help="Commit message.")] = None,
    remote: Annotated[str, typer.Option("--remote", help="Remote to push to.")] = "origin",
    check: Annotated[Optional[str], typer.Option("--check", help="Command to run before committing (e.g. 'pytest').")] = None,
    no_sync: Annotated[bool, typer.Option("--no-sync", help="Skip pull before pushing.")] = False,
):
    """The full shipping flow: sync → check → commit → push.

    Examples:
      rudra git ship "feat: add login"
      rudra git ship "fix: crash" --check "pytest tests/"
      rudra git ship "docs: update" --no-sync
    """
    require_repo()
    branch = current_branch()

    console.print(f"[bold cyan]🚢 Shipping {branch}...[/bold cyan]\n")

    # 1. sync
    if not no_sync:
        console.print("[bold dim]Step 1/4: Syncing with remote...[/bold dim]")
        code, _ = git("rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}")
        if code == 0:
            run(["git", "pull", "--rebase", remote, branch], f"Pulling {remote}/{branch}")
        else:
            console.print("[dim]No upstream set — skipping pull.[/dim]")
    else:
        console.print("[dim]Step 1/4: Skipping sync.[/dim]")

    # 2. check
    if check:
        console.print(f"\n[bold dim]Step 2/4: Running check: {check}[/bold dim]")
        result = subprocess.run(check, shell=True)
        if result.returncode != 0:
            console.print(f"\n[bold red]✗ Check failed (exit {result.returncode}) — aborting ship.[/bold red]")
            raise typer.Exit(result.returncode)
        console.print("[green]✓ Check passed.[/green]")
    else:
        console.print("[dim]Step 2/4: No check configured (use --check 'pytest' to add one).[/dim]")

    # 3. commit
    console.print("\n[bold dim]Step 3/4: Committing...[/bold dim]")
    code, out = git("status", "--porcelain")
    if code == 0 and out.strip():
        run(["git", "add", "-A"], "Staging all changes")
        if message is None:
            message = typer.prompt("Commit message").strip()
            if not message:
                console.print("[red]Empty message — aborting.[/red]")
                raise typer.Exit(1)
        run(["git", "commit", "-m", message], "Committing")
        console.print(f"[green]✓ Committed.[/green]  [dim]{short_hash()}[/dim]  {message[:60]}")
    else:
        console.print("[dim]Nothing to commit — skipping.[/dim]")

    # 4. push
    console.print("\n[bold dim]Step 4/4: Pushing...[/bold dim]")
    run(["git", "push", "-u", remote, branch], f"Pushing {branch}")

    console.print(f"\n[bold green]🚢 Shipped {branch}![/bold green]  [dim]{short_hash()}[/dim]")


# ── oops ──────────────────────────────────────────────────────────────────────

@app.command()
def oops(
    message: Annotated[Optional[str], typer.Option("--message", "-m", help="New commit message.")] = None,
    push: Annotated[bool, typer.Option("--push", "-p", help="Force-push after fixing.")] = False,
):
    """Fix the last commit — add forgotten files or fix the message.

    Stages any currently modified/untracked files and amends the last commit.

    Examples:
      rudra git oops                    # add forgotten files, keep message
      rudra git oops -m "fix: typo"     # also fix the message
      rudra git oops --push             # amend + force-push
    """
    require_repo()

    code, last_msg = git("log", "-1", "--pretty=%s")
    console.print(f"[dim]Last commit:[/dim] {last_msg.strip()}")

    code, out = git("status", "--porcelain")
    has_changes = code == 0 and out.strip()

    if has_changes:
        console.print("[dim]Staging all current changes...[/dim]")
        run(["git", "add", "-A"], "Staging")

    amend_args = ["git", "commit", "--amend"]
    if message:
        amend_args += ["-m", message]
    else:
        amend_args.append("--no-edit")

    run(amend_args, "Amending last commit")
    console.print(f"[bold green]✓ Fixed.[/bold green]  [dim]{short_hash()}[/dim]")

    if push:
        run(["git", "push", "--force-with-lease"], "Force-pushing")


# ── nuke ──────────────────────────────────────────────────────────────────────

@app.command()
def nuke(
    branch: Annotated[Optional[str], typer.Argument(help="Branch to nuke. Defaults to current.")] = None,
    remote: Annotated[str, typer.Option("--remote", help="Remote to delete from.")] = "origin",
    local_only: Annotated[bool, typer.Option("--local", help="Only delete locally.")] = False,
    remote_only: Annotated[bool, typer.Option("--remote-only", help="Only delete from remote.")] = False,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation.")] = False,
):
    """Delete a branch locally AND on the remote in one shot. 💥

    Examples:
      rudra git nuke feature/old-thing
      rudra git nuke feature/x --local        # local only
      rudra git nuke feature/x --remote-only  # remote only
    """
    require_repo()
    target = branch or current_branch()
    default = default_branch()

    if target == default:
        console.print(f"[bold red]⛔ Refusing to nuke '{default}' (default branch).[/bold red]")
        raise typer.Exit(1)

    cur = current_branch()
    scope = "locally and on remote" if not local_only and not remote_only else ("locally" if local_only else "on remote")
    console.print(f"[bold red]💥 About to nuke '{target}' {scope}.[/bold red]")

    if not yes and not typer.confirm("Continue?", default=False):
        raise typer.Exit(0)

    if cur == target and not remote_only:
        run(["git", "checkout", default], f"Switching to {default} first")

    if not remote_only:
        run(["git", "branch", "-D", target], f"Deleting {target} locally")
        console.print(f"[green]✓ Local branch '{target}' deleted.[/green]")

    if not local_only:
        code, out = git("ls-remote", "--heads", remote, target)
        if code == 0 and out.strip():
            run(["git", "push", remote, "--delete", target], f"Deleting {remote}/{target}")
            console.print(f"[green]✓ Remote branch '{remote}/{target}' deleted.[/green]")
        else:
            console.print(f"[dim]Remote branch '{remote}/{target}' doesn't exist — skipping.[/dim]")

    console.print(f"[bold green]💥 Nuked '{target}'.[/bold green]")


# ── yeet ──────────────────────────────────────────────────────────────────────

_YEET_CONFIRMATIONS = [
    "This is a force push. Are you absolutely sure?",
    "Last chance. Really force push?",
    "You realize this rewrites remote history, right?",
]


@app.command()
def yeet(
    remote: Annotated[str, typer.Option("--remote", help="Remote to yeet to.")] = "origin",
    branch: Annotated[Optional[str], typer.Argument(help="Branch to yeet.")] = None,
    skip_drama: Annotated[bool, typer.Option("--yes", "-y", help="Skip the dramatic confirmation.")] = False,
):
    """Force-push with --force-with-lease. 🚀

    Comes with a multi-step confirmation because force pushes are serious business.

    Examples:
      rudra git yeet
      rudra git yeet --yes    # skip the drama
    """
    require_repo()
    cur = branch or current_branch()

    if not skip_drama:
        console.print(f"\n[bold yellow]🚀 YEET — force pushing [cyan]{cur}[/cyan] → [cyan]{remote}[/cyan][/bold yellow]\n")
        for q in _YEET_CONFIRMATIONS:
            if not typer.confirm(q, default=False):
                console.print("[dim]Aborted. Probably the right call.[/dim]")
                raise typer.Exit(0)

    run(["git", "push", "--force-with-lease", remote, cur], f"Force-pushing {cur} → {remote}")
    console.print(f"\n[bold green]🚀 Yeeted {cur} → {remote}.[/bold green]")
    console.print("[dim](with --force-with-lease, so at least you didn't nuke someone else's work)[/dim]")


# ── panic ─────────────────────────────────────────────────────────────────────

@app.command()
def panic():
    """Something went horribly wrong. Interactive recovery menu. 😱

    Shows you what's in your reflog and offers common recovery options.
    """
    require_repo()

    console.print(Panel(
        "[bold red]😱 PANIC MODE[/bold red]\n\n"
        "Take a breath. git almost never actually deletes anything.\n"
        "Everything in your reflog is recoverable.",
        border_style="red",
    ))

    # Show recent reflog
    code, reflog = git("reflog", "--oneline", "-15")
    if code == 0 and reflog.strip():
        console.print("\n[bold dim]Recent reflog (your safety net):[/bold dim]")
        for line in reflog.splitlines():
            parts = line.split(" ", 1)
            if len(parts) == 2:
                console.print(f"  [yellow]{parts[0]}[/yellow]  {parts[1]}")

    console.print("\n[bold]What happened?[/bold]")
    options = [
        ("1", "I accidentally ran `git reset --hard` and lost commits"),
        ("2", "I deleted a branch I needed"),
        ("3", "I force-pushed and overwrote someone's work"),
        ("4", "I committed to the wrong branch"),
        ("5", "I merged the wrong branch"),
        ("6", "I need to find a specific lost commit"),
        ("7", "Nothing above — show me the reflog and I'll figure it out"),
    ]
    for key, desc in options:
        console.print(f"  [cyan]{key}[/cyan]  {desc}")

    choice = typer.prompt("\nWhat happened", default="7").strip()

    console.print()
    if choice == "1":
        console.print("[bold]Recovery: lost commits after reset --hard[/bold]")
        console.print("  Find the commit hash in the reflog above, then:")
        console.print("  [cyan]git checkout -b recovery-branch <hash>[/cyan]")
        console.print("  Or if it was your current branch:")
        console.print("  [cyan]git reset --hard <hash>[/cyan]")
    elif choice == "2":
        console.print("[bold]Recovery: deleted branch[/bold]")
        console.print("  Find the last commit of that branch in the reflog, then:")
        console.print("  [cyan]git checkout -b <branch-name> <hash>[/cyan]")
    elif choice == "3":
        console.print("[bold]Recovery: force push overwrote remote[/bold]")
        console.print("  If you know the old hash (it's in your reflog):")
        console.print("  [cyan]git push --force-with-lease origin <old-hash>:main[/cyan]")
        console.print("  If someone else has the old commits, ask them to push.")
    elif choice == "4":
        branch = current_branch()
        console.print("[bold]Recovery: committed to wrong branch[/bold]")
        console.print(f"  You're on [cyan]{branch}[/cyan]. To move your last commit to another branch:")
        code, sha = git("rev-parse", "HEAD")
        sha = sha.strip()
        console.print(f"  1. Note the commit hash: [yellow]{sha}[/yellow]")
        console.print(f"  2. [cyan]rudra git undo[/cyan]   ← undo it here (soft reset)")
        console.print(f"  3. [cyan]rudra git branch <correct-branch>[/cyan]")
        console.print(f"  4. [cyan]git cherry-pick {sha}[/cyan]")
    elif choice == "5":
        console.print("[bold]Recovery: wrong merge[/bold]")
        console.print("  If you haven't pushed yet:")
        console.print("  [cyan]git reset --hard ORIG_HEAD[/cyan]")
        console.print("  (git saves the pre-merge state in ORIG_HEAD)")
    elif choice == "6":
        console.print("[bold]Recovery: find a lost commit[/bold]")
        console.print("  [cyan]git fsck --lost-found[/cyan]  — shows dangling commits")
        console.print("  [cyan]git reflog[/cyan]             — your full recent history")
    else:
        if code == 0 and reflog.strip():
            console.print("[dim]Full reflog shown above. Find your hash and:[/dim]")
            console.print("  [cyan]git checkout -b recovery <hash>[/cyan]")

    console.print("\n[dim]Still stuck? Try: https://ohshitgit.com[/dim]")


# ── contrib ───────────────────────────────────────────────────────────────────

@app.command()
def contrib(
    n: Annotated[int, typer.Option("--count", "-n", help="Top N contributors.")] = 10,
    since: Annotated[Optional[str], typer.Option("--since", help="E.g. '3 months ago'.")] = None,
    file: Annotated[Optional[str], typer.Option("--file", "-f", help="Limit to a file.")] = None,
):
    """Pretty contribution stats by author. Who wrote this repo?

    Examples:
      rudra git contrib
      rudra git contrib --since "3 months ago"
      rudra git contrib --file src/main.py
    """
    require_repo()

    args = ["shortlog", "-sn", "--no-merges"]
    if since:
        args.append(f"--since={since}")
    if file:
        args += ["--", file]

    code, out = git(*args)
    if code != 0 or not out.strip():
        console.print("[dim]No commits found.[/dim]")
        return

    # Parse shortlog output: "  42\tAuthor Name"
    entries = []
    for line in out.strip().splitlines():
        parts = line.strip().split("\t", 1)
        if len(parts) == 2:
            try:
                count = int(parts[0].strip())
                author = parts[1].strip()
                entries.append((count, author))
            except ValueError:
                continue

    entries = entries[:n]
    if not entries:
        console.print("[dim]No data.[/dim]")
        return

    total = sum(c for c, _ in entries)
    top = entries[0][0]

    table = Table(title="Contributions", show_header=True, header_style="bold dim", box=None)
    table.add_column("#", style="dim", no_wrap=True)
    table.add_column("Author", style="cyan")
    table.add_column("Commits", style="yellow", no_wrap=True)
    table.add_column("Share", no_wrap=True)
    table.add_column("", no_wrap=True)

    for i, (count, author) in enumerate(entries, 1):
        pct = count / total * 100
        bar_len = int(count / top * 20)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        table.add_row(str(i), author, str(count), f"{pct:.1f}%", f"[green]{bar}[/green]")

    console.print()
    console.print(table)
    console.print(f"\n[dim]Total commits: {total}[/dim]" + (f"  [dim]since {since}[/dim]" if since else ""))
    console.print()


# ── time-travel ───────────────────────────────────────────────────────────────

@app.command(name="time-travel")
def time_travel(
    ref: Annotated[Optional[str], typer.Argument(help="Commit hash or ref to travel to. Omit to pick from log.")] = None,
    restore: Annotated[bool, typer.Option("--restore", help="Restore a specific file only.")] = False,
    file: Annotated[Optional[str], typer.Option("--file", "-f", help="File to restore from that commit.")] = None,
):
    """Travel back to any commit in history. 🕰️

    Creates a detached HEAD or, if --file, restores just that file without
    changing your branch.

    Examples:
      rudra git time-travel             # pick from log
      rudra git time-travel abc1234     # go to that commit
      rudra git time-travel --file src/main.py   # restore one file
    """
    require_repo()

    if ref is None:
        code, out = git("log", "--oneline", "--decorate", "-20")
        if code != 0:
            console.print("[red]Could not read log.[/red]")
            raise typer.Exit(1)
        lines = out.splitlines()
        console.print("\n[bold]🕰️  Where do you want to go?[/bold]")
        for i, line in enumerate(lines, 1):
            parts = line.split(" ", 1)
            console.print(f"  [cyan]{i:2}[/cyan]  [yellow]{parts[0]}[/yellow]  {parts[1] if len(parts)>1 else ''}")
        raw = typer.prompt("Choice", default="1").strip()
        try:
            idx = int(raw) - 1
            ref = lines[idx].split()[0]
        except (ValueError, IndexError):
            console.print("[red]Invalid choice.[/red]")
            raise typer.Exit(1)

    if file or restore:
        target_file = file or typer.prompt("File to restore").strip()
        run(["git", "checkout", ref, "--", target_file], f"Restoring {target_file} from {ref}")
        console.print(f"[bold green]✓ Restored {target_file} from {ref}.[/bold green]")
        console.print(f"[dim]File is now staged. Commit when ready, or [bold]rudra git restore --staged {target_file}[/bold] to unstage.[/dim]")
        return

    cur = current_branch()
    console.print(f"\n[bold yellow]🕰️  Travelling to {ref}...[/bold yellow]")
    console.print(f"[dim]You'll be in detached HEAD state. To get back:[/dim]")
    console.print(f"  [cyan]git checkout {cur}[/cyan]")
    console.print(f"  or create a branch here: [cyan]git checkout -b new-branch[/cyan]")

    if not typer.confirm("\nContinue?", default=True):
        raise typer.Exit(0)

    run(["git", "checkout", ref], f"Detaching HEAD at {ref}")
    console.print(f"\n[bold green]🕰️  You're now at {ref}.[/bold green]")
    console.print(f"[dim]To return to {cur}: [bold]git checkout {cur}[/bold][/dim]")


# ── changelog ─────────────────────────────────────────────────────────────────

@app.command()
def changelog(
    since: Annotated[Optional[str], typer.Option("--since", help="Start ref (tag/commit). Defaults to last tag.")] = None,
    until: Annotated[str, typer.Option("--until", help="End ref.")] = "HEAD",
    output: Annotated[Optional[str], typer.Option("--output", "-o", help="Write to file (e.g. CHANGELOG.md).")] = None,
    conventional: Annotated[bool, typer.Option("--conv", help="Group by conventional commit type.")] = True,
):
    """Auto-generate a changelog from commits since the last tag.

    Examples:
      rudra git changelog
      rudra git changelog --since v1.0.0
      rudra git changelog --output CHANGELOG.md
    """
    require_repo()

    if since is None:
        code, last_tag = git("describe", "--tags", "--abbrev=0")
        if code == 0 and last_tag.strip():
            since = last_tag.strip()
            console.print(f"[dim]Generating changelog since {since}...[/dim]")
        else:
            since = ""
            console.print("[dim]No tags found — generating from all commits.[/dim]")

    ref_range = f"{since}..{until}" if since else until
    code, out = git("log", ref_range, "--pretty=format:%h\t%s\t%an", "--no-merges")
    if code != 0 or not out.strip():
        console.print("[dim]No commits found in range.[/dim]")
        return

    commits = []
    for line in out.strip().splitlines():
        parts = line.split("\t", 2)
        if len(parts) == 3:
            commits.append({"hash": parts[0], "subject": parts[1], "author": parts[2]})

    if conventional:
        # Group by conventional commit prefix
        _TYPES = {
            "feat":     ("✨ Features",       []),
            "fix":      ("🐛 Bug Fixes",       []),
            "perf":     ("⚡ Performance",     []),
            "refactor": ("♻️  Refactoring",    []),
            "docs":     ("📝 Documentation",   []),
            "test":     ("🧪 Tests",           []),
            "chore":    ("🔧 Chores",          []),
            "ci":       ("👷 CI",              []),
            "style":    ("💄 Style",           []),
            "revert":   ("⏪ Reverts",         []),
            "other":    ("📦 Other",           []),
        }

        for c in commits:
            matched = False
            for t in _TYPES:
                if t == "other":
                    continue
                if c["subject"].startswith(f"{t}:") or c["subject"].startswith(f"{t}("):
                    # Strip the prefix
                    subject = c["subject"].split(":", 1)[-1].strip()
                    _TYPES[t][1].append(f"- {subject} ([{c['hash']}])")
                    matched = True
                    break
            if not matched:
                _TYPES["other"][1].append(f"- {c['subject']} ([{c['hash']}])")

        lines = [f"## Changelog\n"]
        if since:
            lines[0] = f"## Changelog — {since} → {until}\n"

        for key, (title, items) in _TYPES.items():
            if items:
                lines.append(f"\n### {title}\n")
                lines.extend(items)
    else:
        lines = [f"## Changelog — {since or 'all'} → {until}\n"]
        for c in commits:
            lines.append(f"- {c['subject']} ([{c['hash']}]) — {c['author']}")

    changelog_text = "\n".join(lines)

    console.print()
    console.print(changelog_text)
    console.print()

    if output:
        from pathlib import Path
        p = Path(output)
        existing = p.read_text() if p.exists() else ""
        p.write_text(changelog_text + "\n\n" + existing)
        console.print(f"[bold green]✓ Written to {output}.[/bold green]")
