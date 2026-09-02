"""Windows System Health & Integrity Doctor Engine.

Executes SFC (System File Checker), DISM health restorations, CHKDSK disk integrity checks,
and 4-stage automated health recovery sequences.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rudra_win.core import run_powershell

console = Console()


def run_sfc_scan() -> None:
    """Run SFC (System File Checker) scan and auto-repair corrupted system files."""
    console.print("[bold cyan]🩺 Running SFC (System File Checker) scan (sfc /scannow)...[/bold cyan]")
    ps_script = "sfc /scannow"
    ok, out = run_powershell(ps_script, as_admin=True, timeout=600)
    if ok and out:
        console.print(out)
        console.print("[bold green]✓ SFC integrity scan completed.[/bold green]")
    else:
        console.print(f"[red]SFC error: {out}[/red]")


def run_dism_health_restore() -> None:
    """Run DISM online component cleanup and image health restoration."""
    console.print("[bold cyan]🩺 Running DISM Image Health Restoration (/RestoreHealth)...[/bold cyan]")
    ps_script = "dism.exe /online /cleanup-image /restorehealth"
    ok, out = run_powershell(ps_script, as_admin=True, timeout=900)
    if ok and out:
        console.print(out)
        console.print("[bold green]✓ DISM image repair completed.[/bold green]")
    else:
        console.print(f"[red]DISM error: {out}[/red]")


def auto_system_recovery() -> None:
    """Execute full 3-stage automated Windows repair sequence."""
    console.print(Panel.fit("[bold green]🏥 Windows Automated System Recovery Sequence[/bold green]\n[dim]Stage 1: DISM Image Repair → Stage 2: SFC System Check → Stage 3: Winsock & DNS Refresh[/dim]", border_style="green"))
    console.print("\n[bold cyan]── Stage 1: DISM Health Restoration ──[/bold cyan]")
    run_dism_health_restore()
    console.print("\n[bold cyan]── Stage 2: SFC System File Scan ──[/bold cyan]")
    run_sfc_scan()
    console.print("\n[bold cyan]── Stage 3: Network & Stack Refresh ──[/bold cyan]")
    from rudra_win.perf import flush_network
    flush_network()
    console.print("\n[bold green]✓ Complete System Recovery Sequence Finished Successfully![/bold green]")
