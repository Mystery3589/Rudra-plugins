"""rudra git remote — inspect and convert remote URLs between SSH and HTTPS."""

from __future__ import annotations
import re
import shutil
from pathlib import Path
from typing import Annotated, Optional
import typer
import click
from rich.console import Console
from rudra_git.helpers import git, run, require_repo

# click.Choice does exactly what the old hand-rolled _Choice class did — use it
# directly rather than reaching into typer's internals for a click reference.
_Choice = click.Choice

app = typer.Typer()
console = Console()

_SSH_RE   = re.compile(r"^git@(?P<host>[^:]+):(?P<path>.+?)(?:\.git)?$")
_HTTPS_RE = re.compile(r"^https?://(?P<host>[^/]+)/(?P<path>.+?)(?:\.git)?$")
_KEY_FILES = ["id_ed25519", "id_rsa", "id_ecdsa", "id_dsa", "id_ed25519_sk", "id_ecdsa_sk"]


def _parse(url: str) -> dict | None:
    url = url.strip()
    m = _SSH_RE.match(url)
    if m:
        return {"type": "ssh", "host": m.group("host"), "path": m.group("path")}
    m = _HTTPS_RE.match(url)
    if m:
        return {"type": "https", "host": m.group("host"), "path": m.group("path")}
    return None


def _to_ssh(p: dict) -> str:
    return f"git@{p['host']}:{p['path']}.git"


def _to_https(p: dict) -> str:
    return f"https://{p['host']}/{p['path']}.git"


def _can_ssh() -> bool:
    ssh_dir = Path.home() / ".ssh"
    if ssh_dir.exists() and any((ssh_dir / k).exists() for k in _KEY_FILES):
        return True
    if shutil.which("ssh-add"):
        import subprocess
        r = subprocess.run(["ssh-add", "-l"], capture_output=True)
        return r.returncode == 0
    return False


def _recommend_label(ssh_ok: bool) -> None:
    if ssh_ok:
        console.print("[bold green]Recommendation: SSH[/bold green] — key found, faster and no credential prompts.")
    else:
        console.print("[bold yellow]Recommendation: HTTPS[/bold yellow] — no SSH key found. Use a personal access token.")


def _get_remotes() -> dict[str, str]:
    code, out = git("remote", "-v")
    if code != 0:
        return {}
    remotes: dict[str, str] = {}
    for line in out.splitlines():
        if "(fetch)" not in line:
            continue
        parts = line.split()
        if len(parts) >= 2:
            remotes[parts[0]] = parts[1]
    return remotes


def _handle_one(name: str, url: str, force: str | None, ssh_ok: bool) -> None:
    parsed = _parse(url)
    if parsed is None:
        console.print(f"[dim]{name}: unrecognised URL '{url}' — skipping.[/dim]")
        return

    ssh_url   = _to_ssh(parsed)
    https_url = _to_https(parsed)
    cur_type  = parsed["type"]

    console.print(f"\n[bold]Remote:[/bold] [cyan]{name}[/cyan]")
    console.print(f"  Current : {url}  [dim]({cur_type})[/dim]")
    console.print(f"  SSH     : [green]{ssh_url}[/green]")
    console.print(f"  HTTPS   : [yellow]{https_url}[/yellow]")

    if cur_type == "ssh" and ssh_ok and force != "https":
        console.print("[dim]  → Already SSH with key available. Nothing to do.[/dim]")
        return
    if cur_type == "https" and not ssh_ok and force != "ssh":
        console.print("[dim]  → Already HTTPS and no SSH key. Nothing to do.[/dim]")
        return

    if force in ("ssh", "https"):
        target = force
    elif cur_type == "https" and ssh_ok:
        console.print("[yellow]  ⚠ SSH key available but remote uses HTTPS.[/yellow]")
        _recommend_label(True)
        target = typer.prompt("Convert to", type=_Choice(["ssh", "https", "skip"]), default="ssh")
    elif cur_type == "ssh" and not ssh_ok:
        console.print("[yellow]  ⚠ Remote uses SSH but no SSH key found.[/yellow]")
        _recommend_label(False)
        target = typer.prompt("Convert to", type=_Choice(["ssh", "https", "skip"]), default="https")
    else:
        _recommend_label(ssh_ok)
        target = typer.prompt("Which form", type=_Choice(["ssh", "https", "skip"]),
                              default="ssh" if ssh_ok else "https")

    if target == "skip":
        return

    new_url = ssh_url if target == "ssh" else https_url
    if new_url == url:
        console.print("  [dim]Already in that form — nothing changed.[/dim]")
        return
    run(["git", "remote", "set-url", name, new_url], f"Updating {name}")
    console.print(f"  [bold green]✓[/bold green] {name} → {new_url}")


@app.command()
def remote(
    name: Annotated[str, typer.Argument(help="Remote name.")] = "origin",
    all_remotes: Annotated[bool, typer.Option("--all", "-a", help="Process all remotes.")] = False,
    to_ssh: Annotated[bool, typer.Option("--ssh", help="Force SSH.")] = False,
    to_https: Annotated[bool, typer.Option("--https", help="Force HTTPS.")] = False,
    add: Annotated[Optional[str], typer.Option("--add", help="Add a new remote URL.")] = None,
):
    """Inspect and convert remote URLs between SSH and HTTPS.

    Examples:
      rudra git remote                   # inspect/fix 'origin'
      rudra git remote --all             # all remotes
      rudra git remote --ssh             # force SSH
      rudra git remote upstream --https  # force 'upstream' to HTTPS
      rudra git remote --add git@github.com:user/repo.git
    """
    if not shutil.which("git"):
        console.print("[bold red]git not found.[/bold red]")
        raise typer.Exit(1)
    require_repo()

    if to_ssh and to_https:
        console.print("[red]--ssh and --https are mutually exclusive.[/red]")
        raise typer.Exit(1)
    force = "ssh" if to_ssh else ("https" if to_https else None)
    ssh_ok = _can_ssh()

    if add:
        parsed = _parse(add)
        if parsed is None:
            console.print(f"[red]Couldn't parse URL: {add}[/red]")
            raise typer.Exit(1)
        ssh_url, https_url = _to_ssh(parsed), _to_https(parsed)
        console.print(f"\n[bold]Adding remote:[/bold] [cyan]{name}[/cyan]")
        console.print(f"  SSH   : [green]{ssh_url}[/green]")
        console.print(f"  HTTPS : [yellow]{https_url}[/yellow]")
        _recommend_label(ssh_ok)
        target = force or typer.prompt("Which form", type=_Choice(["ssh", "https"]),
                                       default="ssh" if ssh_ok else "https")
        chosen = ssh_url if target == "ssh" else https_url
        existing = _get_remotes()
        if name in existing:
            if typer.confirm(f"Remote '{name}' exists ({existing[name]}). Overwrite?", default=False):
                run(["git", "remote", "set-url", name, chosen], f"Updating {name}")
        else:
            run(["git", "remote", "add", name, chosen], f"Adding {name}")
        console.print(f"[bold green]✓[/bold green] {name} → {chosen}")
        return

    remotes = _get_remotes()
    if not remotes:
        console.print("[yellow]No remotes configured.[/yellow]")
        _recommend_label(ssh_ok)
        url_input = typer.prompt("\nEnter a remote URL to add (or leave blank to skip)", default="").strip()
        if not url_input:
            return
        parsed = _parse(url_input)
        if parsed is None:
            console.print(f"[red]Couldn't parse: {url_input}[/red]")
            raise typer.Exit(1)
        ssh_url, https_url = _to_ssh(parsed), _to_https(parsed)
        console.print(f"  SSH   : [green]{ssh_url}[/green]")
        console.print(f"  HTTPS : [yellow]{https_url}[/yellow]")
        target = force or typer.prompt("Which form", type=_Choice(["ssh", "https"]),
                                       default="ssh" if ssh_ok else "https")
        chosen = ssh_url if target == "ssh" else https_url
        rname = typer.prompt("Remote name", default="origin")
        run(["git", "remote", "add", rname, chosen], f"Adding {rname}")
        console.print(f"[bold green]✓[/bold green] {rname} → {chosen}")
        return

    if all_remotes:
        for rname, rurl in remotes.items():
            _handle_one(rname, rurl, force, ssh_ok)
    elif name not in remotes:
        console.print(f"[yellow]Remote '{name}' not found.[/yellow]")
        available = list(remotes.keys())
        if available:
            console.print(f"Available: {', '.join(available)}")
            chosen = typer.prompt("Which remote?", default=available[0])
            _handle_one(chosen, remotes[chosen], force, ssh_ok)
    else:
        _handle_one(name, remotes[name], force, ssh_ok)
    console.print()
