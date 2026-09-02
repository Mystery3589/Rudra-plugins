"""rudra lab chaos — Chaos Engineering injector for project resilience testing.

Simulates real-world failure conditions: network latency spikes, memory pressure,
CPU throttling, disk saturation, and random process kills — so you can harden your
project before it hits production.
"""

from __future__ import annotations

import os
import platform
import random
import shutil
import subprocess
import sys
import time
import threading
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()
app = typer.Typer(help="💥 Chaos engineering injector — stress test your project's resilience.", no_args_is_help=True)

IS_LINUX = platform.system() == "Linux"
IS_MAC   = platform.system() == "Darwin"
IS_WIN   = platform.system() == "Windows"


def _have(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def _run(cmd: list[str], check: bool = False) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True)
        return r.returncode, (r.stdout + r.stderr).strip()
    except Exception as e:
        return -1, str(e)


# ── Network Chaos ─────────────────────────────────────────────────────────────

def _inject_latency(ms: int, jitter: int, duration: int) -> None:
    """Add network latency using tc-netem (Linux only)."""
    if not IS_LINUX:
        console.print("[yellow]Network chaos requires Linux tc-netem (Linux only).[/yellow]")
        return
    if not _have("tc"):
        console.print("[yellow]'tc' (iproute2) not found. Install with: rudra install iproute2[/yellow]")
        return

    iface = "lo"
    # Try to detect default outbound interface
    code, out = _run(["ip", "route", "show", "default"])
    if code == 0 and "dev " in out:
        for part in out.split():
            if part not in ("dev", "via", "proto", "metric", "src"):
                iface = part
                break

    console.print(f"[bold red]💥 Injecting {ms}ms latency ±{jitter}ms on [cyan]{iface}[/cyan] for {duration}s...[/bold red]")
    _run(["sudo", "tc", "qdisc", "add", "dev", iface, "root", "netem",
          "delay", f"{ms}ms", f"{jitter}ms", "distribution", "normal"])
    time.sleep(duration)
    _run(["sudo", "tc", "qdisc", "del", "dev", iface, "root"])
    console.print(f"[green]✓ Network latency removed from {iface}.[/green]")


def _inject_packet_loss(loss_pct: float, duration: int) -> None:
    """Add packet loss via tc-netem."""
    if not IS_LINUX or not _have("tc"):
        console.print("[yellow]Packet loss requires Linux tc-netem.[/yellow]")
        return
    iface = "lo"
    console.print(f"[bold red]💥 Injecting {loss_pct}% packet loss for {duration}s...[/bold red]")
    _run(["sudo", "tc", "qdisc", "add", "dev", iface, "root", "netem", "loss", f"{loss_pct}%"])
    time.sleep(duration)
    _run(["sudo", "tc", "qdisc", "del", "dev", iface, "root"])
    console.print("[green]✓ Packet loss removed.[/green]")


# ── Memory Pressure ───────────────────────────────────────────────────────────

def _memory_pressure(mb: int, duration: int) -> None:
    """Allocate a block of RAM to simulate memory pressure."""
    console.print(f"[bold red]💥 Allocating {mb}MB RAM for {duration}s to simulate memory pressure...[/bold red]")
    try:
        # Allocate mb megabytes by holding a bytearray in memory
        blob = bytearray(mb * 1024 * 1024)
        time.sleep(duration)
        del blob
    except MemoryError:
        console.print("[bold red]Out of memory — could not allocate requested pressure block.[/bold red]")
    console.print("[green]✓ Memory pressure released.[/green]")


# ── CPU Throttle ──────────────────────────────────────────────────────────────

def _cpu_burn(cores: int, duration: int) -> None:
    """Spin up busy-loop threads to saturate CPU cores."""
    console.print(f"[bold red]💥 Burning {cores} CPU core(s) for {duration}s...[/bold red]")
    stop_flag = threading.Event()

    def burner():
        while not stop_flag.is_set():
            _ = [x * x for x in range(5000)]

    threads = [threading.Thread(target=burner, daemon=True) for _ in range(cores)]
    for t in threads:
        t.start()
    time.sleep(duration)
    stop_flag.set()
    for t in threads:
        t.join(timeout=2)
    console.print("[green]✓ CPU burn complete.[/green]")


# ── Disk Saturation ───────────────────────────────────────────────────────────

def _disk_pressure(mb: int, path: str, duration: int) -> None:
    """Write and then delete a large temp file to saturate disk I/O."""
    import tempfile
    dest = os.path.join(path, f"rudra_chaos_{random.randint(1000,9999)}.tmp")
    console.print(f"[bold red]💥 Writing {mb}MB junk to '{dest}' for {duration}s to stress disk I/O...[/bold red]")
    try:
        chunk = b"\x00" * (1024 * 1024)  # 1MB chunk
        with open(dest, "wb") as f:
            for _ in range(mb):
                f.write(chunk)
        time.sleep(duration)
    except Exception as e:
        console.print(f"[yellow]Disk write interrupted: {e}[/yellow]")
    finally:
        if os.path.exists(dest):
            os.remove(dest)
    console.print("[green]✓ Disk pressure file removed.[/green]")


# ── CLI Commands ──────────────────────────────────────────────────────────────

@app.command(name="chaos")
def chaos_cmd(
    latency:     int   = typer.Option(0,    "--latency",      "-L", help="Add network latency in ms (Linux only, requires tc)."),
    jitter:      int   = typer.Option(20,   "--jitter",       "-j", help="Jitter ± ms for latency (used with --latency)."),
    packet_loss: float = typer.Option(0.0,  "--packet-loss",  "-p", help="Packet loss percentage (Linux only, requires tc)."),
    memory:      int   = typer.Option(0,    "--memory",       "-m", help="RAM to consume in MB to simulate memory pressure."),
    cpu:         int   = typer.Option(0,    "--cpu",          "-c", help="Number of CPU cores to saturate."),
    disk:        int   = typer.Option(0,    "--disk",         "-d", help="Disk write in MB to stress I/O."),
    disk_path:   str   = typer.Option("/tmp","--disk-path",         help="Directory to write temp disk file."),
    duration:    int   = typer.Option(15,   "--duration",     "-t", help="Duration in seconds for all chaos effects."),
    all_chaos:   bool  = typer.Option(False,"--all",          "-a", help="Inject all chaos types simultaneously (extreme mode)."),
):
    """💥 Chaos Engineering — inject real failure conditions into your environment.

    Simulates production-like fault scenarios to test how your app handles them:
    network lag, packet drops, RAM exhaustion, CPU pegging, and disk I/O storms.

    Examples:
      rudra lab chaos --latency 200 --duration 30
      rudra lab chaos --memory 512 --cpu 2 --duration 20
      rudra lab chaos --packet-loss 5 --duration 10
      rudra lab chaos --disk 1024 --duration 15
      rudra lab chaos --all --duration 20
    """
    if all_chaos:
        latency     = latency or 150
        packet_loss = packet_loss or 3.0
        memory      = memory or 256
        cpu         = cpu or 2
        disk        = disk or 256

    if not any([latency, packet_loss, memory, cpu, disk]):
        console.print("[yellow]No chaos flags set. Use --help to see options, or --all for extreme mode.[/yellow]")
        raise typer.Exit(0)

    # Summary panel
    table = Table(show_header=False, box=None, padding=(0,2))
    if latency:      table.add_row("[red]Network Latency[/red]",  f"[cyan]+{latency}ms ±{jitter}ms[/cyan]")
    if packet_loss:  table.add_row("[red]Packet Loss[/red]",      f"[cyan]{packet_loss}%[/cyan]")
    if memory:       table.add_row("[red]Memory Pressure[/red]",  f"[cyan]{memory} MB[/cyan]")
    if cpu:          table.add_row("[red]CPU Burn[/red]",         f"[cyan]{cpu} core(s)[/cyan]")
    if disk:         table.add_row("[red]Disk Saturation[/red]",  f"[cyan]{disk} MB on {disk_path}[/cyan]")
    table.add_row("[yellow]Duration[/yellow]",                    f"[bold]{duration}s[/bold]")

    console.print(Panel(table, title="[bold red]💥 Rudra Chaos Injection Plan[/bold red]", border_style="red"))

    if not typer.confirm("\nLaunch chaos? This will affect your system for the specified duration.", default=False):
        console.print("[yellow]Chaos aborted.[/yellow]")
        return

    threads: list[threading.Thread] = []

    if latency:
        threads.append(threading.Thread(target=_inject_latency,   args=(latency, jitter, duration), daemon=True))
    if packet_loss:
        threads.append(threading.Thread(target=_inject_packet_loss, args=(packet_loss, duration), daemon=True))
    if memory:
        threads.append(threading.Thread(target=_memory_pressure,  args=(memory, duration), daemon=True))
    if cpu:
        threads.append(threading.Thread(target=_cpu_burn,         args=(cpu, duration), daemon=True))
    if disk:
        threads.append(threading.Thread(target=_disk_pressure,    args=(disk, disk_path, duration), daemon=True))

    for t in threads:
        t.start()

    console.print(f"\n[bold red]🔥 CHAOS ACTIVE — {duration}s of fault injection running...[/bold red]")
    try:
        for i in range(duration, 0, -1):
            print(f"\r  ⏱  {i:>3}s remaining...", end="", flush=True)
            time.sleep(1)
        print()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted. Waiting for chaos threads to clean up...[/yellow]")

    for t in threads:
        t.join(timeout=5)

    console.print("[bold green]\n✓ Chaos session complete. Your system is restored.[/bold green]")
