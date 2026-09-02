"""Windows Background Services Management Engine.

Audit services, disable non-essential background daemons, and trigger temporary
ultra-low-overhead 'Gaming / High-Throughput' service modes.
"""

from __future__ import annotations

from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rudra_win.core import run_powershell

console = Console()

NON_ESSENTIAL_SERVICES = [
    ("DiagTrack", "Connected User Experiences and Telemetry"),
    ("dmwappushservice", "WAP Push Message Routing Service"),
    ("Spooler", "Print Spooler (if no printer used)"),
    ("MapsBroker", "Downloaded Maps Manager"),
    ("Fax", "Fax Service"),
    ("RemoteRegistry", "Remote Registry Service"),
    ("WbioSrvc", "Windows Biometric Service (if no fingerprint/facecam used)"),
    ("RetailDemo", "Retail Demo Service"),
]


def list_services_cli(search: Optional[str] = None) -> None:
    """List Windows services with search filtering."""
    filter_expr = f'Where-Object {{ $_.Name -like "*{search}*" -or $_.DisplayName -like "*{search}*" }} |' if search else ""
    console.print(Panel.fit(f"[bold cyan]⚙️ Windows Services Overview {'(Filter: ' + search + ')' if search else ''}[/bold cyan]", border_style="cyan"))
    ps_script = f"""
    Get-Service | {filter_expr} Select-Object Name, DisplayName, Status, StartType | Format-Table -AutoSize
    """
    ok, out = run_powershell(ps_script)
    if ok and out:
        console.print(out)


def control_service(name: str, action: str) -> None:
    """Control a service: start, stop, restart, disable, or enable."""
    action_l = action.lower()
    console.print(f"[bold cyan]Applying action '{action_l}' to service '{name}'...[/bold cyan]")
    if action_l == "stop":
        ps_script = f"Stop-Service -Name '{name}' -Force"
    elif action_l == "start":
        ps_script = f"Start-Service -Name '{name}'"
    elif action_l == "restart":
        ps_script = f"Restart-Service -Name '{name}' -Force"
    elif action_l == "disable":
        ps_script = f"Stop-Service -Name '{name}' -Force -ErrorAction SilentlyContinue; Set-Service -Name '{name}' -StartupType Disabled"
    elif action_l == "enable":
        ps_script = f"Set-Service -Name '{name}' -StartupType Automatic; Start-Service -Name '{name}'"
    else:
        console.print(f"[bold red]Unknown action '{action}'. Choose: start, stop, restart, disable, enable[/bold red]")
        return
    ok, out = run_powershell(ps_script, as_admin=True)
    if ok:
        console.print(f"[bold green]✓ Service '{name}' {action_l} complete![/bold green]")
    else:
        console.print(f"[red]Error: {out}[/red]")


def enable_gaming_mode_services() -> None:
    """Temporarily stop heavy background services to maximize CPU/RAM headroom."""
    console.print(Panel.fit("[bold green]🎮 Engaging Ultra-Low-Overhead Gaming/Throughput Mode[/bold green]\n[dim]Temporarily halting non-critical background services...[/dim]", border_style="green"))
    ps_script = """
    $services = @('Spooler', 'MapsBroker', 'Fax', 'RemoteRegistry', 'RetailDemo')
    foreach ($s in $services) {
        Stop-Service -Name $s -Force -ErrorAction SilentlyContinue
        Write-Host "Stopped $s"
    }
    """
    ok, out = run_powershell(ps_script, as_admin=True)
    if ok:
        console.print("[bold green]✓ Non-essential background services stopped. Maximum system resources dedicated to foreground tasks.[/bold green]")
    else:
        console.print(f"[red]Error: {out}[/red]")
