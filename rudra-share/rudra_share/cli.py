"""CLI interface for rudra-share ('rudra share' / 'rudra tunnel')."""

from __future__ import annotations

from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from rudra_share import qr, tunnel

console = Console()
app = typer.Typer(
    name="share",
    help="🌐 Instant zero-config public tunneling & port sharing.",
    no_args_is_help=True,
)


def _t():
    try:
        from rudra.theme import get_current_theme
        return get_current_theme()
    except Exception:
        from rudra.theme import ThemeConfig
        return ThemeConfig()


@app.callback(invoke_without_command=True)
def default_share(
    ctx: typer.Context,
    port: Annotated[Optional[int], typer.Argument(help="Local port to share (e.g. 3000, 8080).")] = None,
    show_qr: Annotated[bool, typer.Option("--qr", "-q", help="Show terminal QR code for easy mobile opening.")] = False,
    backend: Annotated[str, typer.Option("--backend", "-b", help="Tunnel backend: auto, localhost.run, cloudflare.")] = "auto",
):
    """If called with a port directly: 'rudra share 3000'."""
    if ctx.invoked_subcommand is None:
        if port is not None:
            share_port(port=port, show_qr=show_qr, backend=backend)
        else:
            console.print(ctx.get_help())


@app.command(name="port")
def share_port(
    port: Annotated[int, typer.Argument(help="Local port to share publicly.")],
    show_qr: Annotated[bool, typer.Option("--qr", "-q", help="Show terminal QR code.")] = False,
    backend: Annotated[str, typer.Option("--backend", "-b", help="Tunnel backend: auto, localhost.run, cloudflare.")] = "auto",
):
    """Expose a local port to a secure public HTTPS URL."""
    th = _t()
    console.print(f"[bold {th.primary}]{th.prompt_char} Launching public tunnel for localhost:{port}...[/bold {th.primary}]")

    res = tunnel.start_tunnel(port, backend=backend)
    if not res["success"]:
        console.print(f"[bold {th.error}]✖ {res.get('error')}[/bold {th.error}]")
        raise typer.Exit(1)

    t_info = res["tunnel"]
    public_url = t_info["url"]

    body = (
        f"[bold]Local Target:[/bold]     http://localhost:{port}\n"
        f"[bold]Public HTTPS URL:[/bold] [bold {th.accent}]{public_url}[/bold {th.accent}]\n"
        f"[bold]Backend:[/bold]          {t_info['backend']}\n"
        f"[bold]Process PID:[/bold]      {t_info['pid']}\n"
        f"[{th.dim}]To stop this tunnel: [bold]rudra share stop {port}[/bold][/{th.dim}]"
    )

    console.print()
    console.print(
        Panel(
            body,
            title=f"[{th.primary}]{th.prompt_char} Active Public Tunnel[/{th.primary}]",
            border_style=th.panel_border,
        )
    )

    if show_qr:
        console.print(f"\n[bold {th.secondary}]📱 Scan with your phone to open:[/bold {th.secondary}]")
        qr_text = qr.render_terminal_qr(public_url)
        if qr_text:
            console.print(qr_text)
        else:
            console.print(f"[{th.dim}]QR generation unavailable.[/{th.dim}]")


@app.command(name="list")
@app.command(name="status")
def list_cmd():
    """List all currently active public tunnels."""
    th = _t()
    active = tunnel.list_tunnels()
    if not active:
        console.print(f"[{th.warning}]No active public tunnels running.[/{th.warning}]")
        console.print(f"[{th.dim}]Start one with: [bold]rudra share <port>[/bold] (e.g. rudra share 3000)[/{th.dim}]")
        return

    table = Table(
        title=f"[{th.table_header}]{th.prompt_char} Active Public Tunnels ({len(active)})[/{th.table_header}]",
        border_style=th.panel_border,
        show_lines=True,
    )
    table.add_column("Port", style="bold", justify="center")
    table.add_column("Public HTTPS URL", style=f"bold {th.accent}")
    table.add_column("Backend", style=th.secondary)
    table.add_column("PID", style="dim", justify="center")
    table.add_column("Started", style="dim")

    for t in active:
        table.add_row(
            str(t["port"]),
            t["url"],
            t.get("backend", "—"),
            str(t.get("pid", "—")),
            t.get("started_at", "—"),
        )
    console.print(table)


@app.command(name="stop")
def stop_cmd(
    target: Annotated[str, typer.Argument(help="Port number to stop, or 'all'.")] = "all",
):
    """Stop one or all active public tunnels."""
    th = _t()
    stopped = tunnel.stop_tunnel(target)
    if stopped:
        console.print(f"[bold {th.success}]✓ Stopped tunnel(s) on port(s): {', '.join(map(str, stopped))}[/bold {th.success}]")
    else:
        console.print(f"[{th.warning}]No matching active tunnels found for '{target}'.[/{th.warning}]")


@app.command(name="qr")
def qr_cmd(url: Annotated[str, typer.Argument(help="URL or text to render as a terminal QR code.")]):
    """Display a high-contrast terminal QR code for any URL."""
    th = _t()
    console.print(f"[{th.secondary}]Generating QR code for: {url}[/{th.secondary}]\n")
    qr_text = qr.render_terminal_qr(url)
    if qr_text:
        console.print(qr_text)
    else:
        console.print(f"[bold {th.error}]Could not generate QR code.[/{th.error}]")
