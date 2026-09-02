"""CLI entry point for Rudra Terminal Web UI."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import Annotated, Optional

import typer
import uvicorn
from rich.console import Console
from rich.panel import Panel

try:
    from rudra.web.auth import get_server_token, set_server_token
    from rudra.web.server import app
except ImportError:
    from rudra_web.auth import get_server_token, set_server_token
    from rudra_web.server import app

console = Console()
cli_app = typer.Typer(
    name="web",
    help="🌐 Rudra Terminal Web UI — Schema-Driven Terminal Web Interface.",
    no_args_is_help=False,
)

PID_DIR = Path.home() / ".rudra" / "web"
PID_FILE = PID_DIR / "rudra-web.pid"
LOG_FILE = PID_DIR / "rudra-web.log"


def _read_pid() -> Optional[int]:
    if not PID_FILE.exists():
        return None
    try:
        pid = int(PID_FILE.read_text().strip())
        os.kill(pid, 0)
        return pid
    except (ValueError, ProcessLookupError, PermissionError):
        PID_FILE.unlink(missing_ok=True)
        return None


@cli_app.callback(invoke_without_command=True)
def web_default(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        serve_cmd()


@cli_app.command(name="serve")
@cli_app.command(name="start")
def serve_cmd(
    host: Annotated[str, typer.Option("--host", "-H", help="Host interface to bind (127.0.0.1 for local, 0.0.0.0 for network access).")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port", "-p", help="Port to bind the web interface to.")] = 7070,
    token: Annotated[Optional[str], typer.Option("--token", "-t", help="Custom auth token for remote connections.")] = None,
    no_browser: Annotated[bool, typer.Option("--no-browser", help="Do not automatically open dashboard in default browser.")] = False,
    foreground: Annotated[bool, typer.Option("--fg", "--foreground", help="Run in foreground (blocks terminal).")] = False,
):
    """Start the Rudra Terminal Web UI server (runs in background daemon mode by default)."""
    if token:
        set_server_token(token)
    active_token = get_server_token()

    is_remote = host not in ("127.0.0.1", "localhost")
    url = f"http://{host}:{port}"
    local_url = f"http://localhost:{port}"

    existing_pid = _read_pid()
    if existing_pid:
        console.print(f"[yellow]Rudra Web is already running[/yellow] (PID [cyan]{existing_pid}[/cyan])")
        console.print(f"[dim]URL:[/dim] [bold underline green]{url}[/bold underline green]")
        console.print("[dim]Use [bold]rudra web stop[/bold] to stop it, or [bold]rudra web status[/bold] to check it.[/dim]")
        if not no_browser and not is_remote:
            try:
                webbrowser.open(local_url)
            except Exception:
                pass
        return

    if not foreground:
        PID_DIR.mkdir(parents=True, exist_ok=True)
        py_runner = (
            "import uvicorn\n"
            "try:\n"
            "    from rudra.web.server import app\n"
            "except ImportError:\n"
            "    from rudra_web.server import app\n"
            f"uvicorn.run(app, host={host!r}, port={port}, log_level='warning')"
        )
        cmd = [sys.executable, "-c", py_runner]
        log_fh = open(LOG_FILE, "a")
        proc = subprocess.Popen(
            cmd,
            stdout=log_fh,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
        PID_FILE.write_text(str(proc.pid))

        console.print(
            Panel.fit(
                f"[bold green]✓ Rudra Web started in background[/bold green] (PID: [cyan]{proc.pid}[/cyan])\n\n"
                f"[bold cyan]URL:[/bold cyan] [bold underline green]{url}[/bold underline green]\n"
                + (f"[bold yellow]🔑 Remote Auth Token:[/bold yellow] [bold white]{active_token}[/bold white]\n" if is_remote else "")
                + f"[dim]Logs: {LOG_FILE}[/dim]\n"
                f"[dim]Run [bold]rudra web stop[/bold] to terminate.[/dim]",
                border_style="green",
            )
        )
        if not no_browser and not is_remote:
            try:
                webbrowser.open(local_url)
            except Exception:
                pass
        return

    # Foreground Mode
    console.print(
        Panel.fit(
            f"[bold cyan]🔱 Rudra Terminal Web UI Server[/bold cyan]\n\n"
            f"[bold green]▶ Running at:[/bold green] [underline cyan]{url}[/underline cyan]\n"
            + (f"[bold yellow]🔑 Remote Auth Token:[/bold yellow] [bold white]{active_token}[/bold white]\n" if is_remote else "[dim]Localhost mode: Auth bypassed for local browser[/dim]\n")
            + f"[dim]Press Ctrl+C to terminate the server[/dim]",
            border_style="cyan",
        )
    )

    if not no_browser and not is_remote:
        try:
            webbrowser.open(local_url)
        except Exception:
            pass

    uvicorn.run(app, host=host, port=port, log_level="warning")


@cli_app.command(name="stop")
def stop_cmd():
    """Stop the background Rudra Web server."""
    pid = _read_pid()
    if not pid:
        console.print("[dim]Rudra Web is not running.[/dim]")
        return

    try:
        os.kill(pid, signal.SIGTERM)
        PID_FILE.unlink(missing_ok=True)
        console.print(f"[bold green]✓ Stopped Rudra Web server[/bold green] (PID [cyan]{pid}[/cyan])")
    except Exception as e:
        console.print(f"[bold red]Error stopping server (PID {pid}):[/bold red] {e}")


@cli_app.command(name="status")
def status_cmd():
    """Show whether the Rudra Web server is running."""
    pid = _read_pid()
    if pid:
        console.print(f"[bold green]● Rudra Web is running[/bold green] (PID [cyan]{pid}[/cyan])")
    else:
        console.print("[dim]○ Rudra Web is stopped.[/dim]")
