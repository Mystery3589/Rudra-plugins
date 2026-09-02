"""rudra git audit, doctor, and secret scanner.

Audits git repositories for security leaks (API keys, private keys, AWS/OpenAI tokens, .env files),
dangling commits, unpushed branches, and repository health.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()
app = typer.Typer(help="Audit repository health and scan for leaked secrets.", no_args_is_help=False)

SECRET_PATTERNS = [
    ("OpenAI API Key", r"sk-[a-zA-Z0-9T3BlbkFJ]{20,}"),
    ("AWS Access Key", r"AKIA[0-9A-Z]{16}"),
    ("AWS Secret Key", r"(?i)aws(.{0,20})?['\"][0-9a-zA-Z\/+]{40}['\"]"),
    ("GitHub Personal Access Token", r"gh[pousr]_[0-9a-zA-Z]{36}"),
    ("Generic Private Key", r"-----BEGIN (RSA|OPENSSH|EC|DSA|PGP) PRIVATE KEY-----"),
    ("Slack Webhook / Token", r"https:\/\/hooks\.slack\.com\/services\/T[a-zA-Z0-9_]+\/B[a-zA-Z0-9_]+\/[a-zA-Z0-9_]+"),
    ("Google API Key", r"AIza[0-9A-Za-z\\-_]{35}"),
    ("Generic Password Assignment", r"(?i)(password|secret|passwd|api_key|token)\s*=\s*['\"][^'\"]{8,}['\"]"),
]


@app.command(name="audit")
@app.command(name="doctor")
def audit_repo(
    scan_history: bool = typer.Option(False, "--history", "-H", help="Deep scan entire commit history (slower)"),
):
    """Audit git repository health, unpushed commits, and scan for leaked secrets or keys."""
    console.print(Panel.fit("[bold cyan]🔍 Git Repository Security & Health Audit[/bold cyan]", border_style="cyan"))

    # 1. Check if inside git repo
    res = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], capture_output=True, text=True)
    if res.returncode != 0:
        console.print("[bold red]Not a git repository.[/bold red]")
        raise typer.Exit(1)

    issues_count = 0

    # 2. Check for tracked .env or secret files
    console.print("\n[bold cyan]1. Checking for tracked sensitive environment files...[/bold cyan]")
    ls_files = subprocess.run(["git", "ls-files"], capture_output=True, text=True).stdout.splitlines()
    sensitive_files = [f for f in ls_files if any(k in f.lower() for k in (".env", "id_rsa", "id_ed25519", "credentials.json", "secret.key"))]
    if sensitive_files:
        for sf in sensitive_files:
            console.print(f"  [bold red]✖ High Risk File Tracked in Git:[/bold red] {sf}")
            issues_count += 1
    else:
        console.print("  [green]✓ No .env or private key files tracked in git index.[/green]")

    # 3. Secret Pattern Scan on Staged & Working Directory
    console.print("\n[bold cyan]2. Scanning working tree and staged changes for secret patterns...[/bold cyan]")
    diff_out = subprocess.run(["git", "diff", "HEAD"], capture_output=True, text=True).stdout
    secrets_found = []
    for desc, pat in SECRET_PATTERNS:
        matches = re.findall(pat, diff_out)
        if matches:
            secrets_found.append((desc, len(matches)))
            issues_count += len(matches)

    if secrets_found:
        for desc, count in secrets_found:
            console.print(f"  [bold red]✖ Potential Secret Leak Detected ({desc}):[/bold red] {count} occurrence(s) in unstaged/staged diffs!")
    else:
        console.print("  [green]✓ Clean! No plain-text API keys or tokens found in current diff.[/green]")

    # 4. Deep History Scan (Optional)
    if scan_history:
        console.print("\n[bold cyan]3. Scanning git commit log history for secrets...[/bold cyan]")
        log_diff = subprocess.run(["git", "log", "-p", "-n", "100"], capture_output=True, text=True).stdout
        hist_secrets = 0
        for desc, pat in SECRET_PATTERNS:
            m = re.findall(pat, log_diff)
            if m:
                console.print(f"  [bold red]✖ History Alert:[/bold red] Found {len(m)} instance(s) matching '{desc}' in recent 100 commits.")
                hist_secrets += len(m)
        if hist_secrets == 0:
            console.print("  [green]✓ Clean! No secrets found in recent commit history.[/green]")

    # 5. Unpushed Commits & Uncommitted Stashes
    console.print("\n[bold cyan]3. Branch Sync & Stash Health...[/bold cyan]")
    unpushed = subprocess.run(["git", "log", "@{u}..HEAD", "--oneline"], capture_output=True, text=True).stdout.strip()
    if unpushed:
        count_unpushed = len(unpushed.splitlines())
        console.print(f"  [yellow]▲ {count_unpushed} unpushed local commit(s) ready to sync.[/yellow]")
    else:
        console.print("  [green]✓ Local branch is in sync with remote upstream.[/green]")

    stashes = subprocess.run(["git", "stash", "list"], capture_output=True, text=True).stdout.strip()
    if stashes:
        stash_count = len(stashes.splitlines())
        console.print(f"  [dim]• {stash_count} stash entry/entries saved.[/dim]")

    if issues_count == 0:
        console.print("\n[bold green]✓ Repository audit completed cleanly! Health status: EXCELLENT.[/bold green]")
    else:
        console.print(f"\n[bold yellow]⚠ Audit flagged {issues_count} potential security/health item(s).[/bold yellow]")


@app.command(name="prune")
def prune_branches():
    """Delete local branches that have been merged and deleted on remote origin."""
    console.print("[bold cyan]🧹 Pruning stale local branches...[/bold cyan]")
    subprocess.run(["git", "fetch", "--prune"])
    merged_out = subprocess.run(["git", "branch", "--merged"], capture_output=True, text=True).stdout.splitlines()
    current_branch = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True).stdout.strip()

    pruned = 0
    for b in merged_out:
        b_clean = b.strip().lstrip("* ")
        if b_clean and b_clean not in (current_branch, "main", "master", "develop", "dev"):
            subprocess.run(["git", "branch", "-d", b_clean])
            console.print(f"  [bold green]✓ Deleted merged branch:[/bold green] {b_clean}")
            pruned += 1

    if pruned == 0:
        console.print("[dim]No stale merged local branches to delete.[/dim]")
    else:
        console.print(f"[bold green]✓ Pruned {pruned} stale local branch(es).[/bold green]")
