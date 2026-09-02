"""CLI commands for managing the Rudra Web Dashboard."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()
app = typer.Typer(
    name="web",
    help="Modern local web interface & dashboard for Rudra.",
    no_args_is_help=False,
)

# PID file location
_PID_DIR = Path.home() / ".rudra" / "web"
_PID_FILE = _PID_DIR / "rudra-web.pid"
_LOG_FILE = _PID_DIR / "rudra-web.log"


def _read_pid() -> int | None:
    """Read PID from file, return None if not found or stale."""
    if not _PID_FILE.exists():
        return None
    try:
        pid = int(_PID_FILE.read_text().strip())
        # Check if process is actually alive
        os.kill(pid, 0)
        return pid
    except (ValueError, ProcessLookupError, PermissionError):
        _PID_FILE.unlink(missing_ok=True)
        return None


def _write_pid(pid: int) -> None:
    _PID_DIR.mkdir(parents=True, exist_ok=True)
    _PID_FILE.write_text(str(pid))


@app.callback(invoke_without_command=True)
def web_main(ctx: typer.Context):
    """Launch the Rudra Web Dashboard in the background."""
    if ctx.invoked_subcommand is None:
        start_cmd()


@app.command(name="start")
def start_cmd(
    port: Annotated[int, typer.Option("--port", "-p", help="Port to bind the web interface to.")] = 8080,
    host: Annotated[str, typer.Option("--host", "-H", help="Host interface to bind (default: 127.0.0.1).")] = "127.0.0.1",
    open_browser: Annotated[bool, typer.Option("--open/--no-open", help="Automatically open dashboard in default browser.")] = True,
    foreground: Annotated[bool, typer.Option("--fg", help="Run in foreground (blocks the terminal).")] = False,
):
    """Start the Rudra Web Dashboard server (background daemon by default)."""
    url = f"http://{host}:{port}"

    # Check if already running
    existing_pid = _read_pid()
    if existing_pid:
        console.print(f"[yellow]Rudra Web is already running[/yellow] (PID [cyan]{existing_pid}[/cyan])")
        console.print(f"[dim]Dashboard:[/dim] [bold underline green]{url}[/bold underline green]")
        console.print("[dim]Use [bold]rudra web stop[/bold] to stop it first.[/dim]")
        return

    if foreground:
        # --- Foreground mode (old behaviour, blocks terminal) ---
        console.print(
            Panel.fit(
                f"[bold cyan]⚡ Rudra Web Dashboard[/bold cyan] [dim](foreground)[/dim]\n"
                f"[dim]URL:[/dim] [bold underline green]{url}[/bold underline green]\n"
                f"[dim]Press Ctrl+C to stop.[/dim]",
                border_style="cyan",
            )
        )
        if open_browser:
            try:
                webbrowser.open(url)
            except Exception:
                pass
        from rudra_web.server import run_dashboard_server
        server = run_dashboard_server(host=host, port=port)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopping Rudra Web Dashboard...[/yellow]")
            server.server_close()
        return

    # --- Daemon / background mode ---
    _PID_DIR.mkdir(parents=True, exist_ok=True)
    log_file = open(_LOG_FILE, "w")

    # Launch a detached subprocess that runs the server
    proc = subprocess.Popen(
        [
            sys.executable,
            "-c",
            (
                f"import sys; sys.path.insert(0, '{Path(__file__).parent.parent!s}');"
                f"from rudra_web.server import run_dashboard_server;"
                f"srv = run_dashboard_server('{host}', {port});"
                f"srv.serve_forever()"
            ),
        ],
        stdout=log_file,
        stderr=log_file,
        stdin=subprocess.DEVNULL,
        start_new_session=True,   # detach from current terminal session
    )

    _write_pid(proc.pid)

    console.print(
        Panel.fit(
            f"[bold cyan]⚡ Rudra Web Dashboard[/bold cyan] [dim](background)[/dim]\n"
            f"[dim]URL:[/dim]  [bold underline green]{url}[/bold underline green]\n"
            f"[dim]PID:[/dim]  [cyan]{proc.pid}[/cyan]\n"
            f"[dim]Log:[/dim]  [dim]{_LOG_FILE}[/dim]\n"
            f"[dim]Stop:[/dim] [bold]rudra web stop[/bold]",
            border_style="cyan",
        )
    )

    if open_browser:
        import time
        time.sleep(0.5)   # give server a moment to bind
        try:
            webbrowser.open(url)
        except Exception:
            pass


@app.command(name="stop")
def stop_cmd():
    """Stop the background Rudra Web Dashboard server."""
    pid = _read_pid()
    if pid is None:
        console.print("[yellow]Rudra Web is not running.[/yellow]")
        raise typer.Exit(0)

    try:
        os.kill(pid, signal.SIGTERM)
        _PID_FILE.unlink(missing_ok=True)
        console.print(f"[green]✓ Rudra Web stopped[/green] (PID [cyan]{pid}[/cyan] terminated)")
    except ProcessLookupError:
        _PID_FILE.unlink(missing_ok=True)
        console.print("[dim]Process was already gone. PID file removed.[/dim]")
    except PermissionError:
        console.print(f"[red]Permission denied when trying to stop PID {pid}.[/red]")
        raise typer.Exit(1)


@app.command(name="status")
def status_cmd():
    """Show whether the Rudra Web Dashboard is running."""
    pid = _read_pid()
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="dim")
    table.add_column("Value", style="bold")

    if pid:
        table.add_row("Status", "[green]● running[/green]")
        table.add_row("PID", f"[cyan]{pid}[/cyan]")
        table.add_row("Dashboard URL", "[underline green]http://127.0.0.1:8080[/underline green]")
        table.add_row("Log", str(_LOG_FILE))
    else:
        table.add_row("Status", "[red]○ stopped[/red]")

    console.print(table)


@app.command(name="logs")
def logs_cmd(
    follow: Annotated[bool, typer.Option("--follow", "-f", help="Follow the log output (like tail -f).")] = False,
):
    """Show the Rudra Web Dashboard server logs."""
    if not _LOG_FILE.exists():
        console.print("[dim]No log file found. The server has not been started yet.[/dim]")
        raise typer.Exit(0)

    if follow:
        import subprocess as sp
        try:
            sp.run(["tail", "-f", str(_LOG_FILE)])
        except KeyboardInterrupt:
            pass
    else:
        console.print(_LOG_FILE.read_text(encoding="utf-8", errors="replace") or "[dim](empty)[/dim]")
