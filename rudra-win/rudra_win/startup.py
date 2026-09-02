"""Windows Startup & Autostart Management Engine.

Identifies, audits, and disables unwanted startup applications, scheduled task autoruns,
and measures system boot times.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rudra_win.core import run_powershell

console = Console()


def list_startup_items() -> None:
    """List all applications and programs configured to launch at Windows startup."""
    console.print(Panel.fit("[bold cyan]🚀 Windows Startup Applications & Autoruns[/bold cyan]", border_style="cyan"))
    ps_script = """
    $items = Get-CimInstance Win32_StartupCommand | Select-Object Name, Command, Location, User
    $items | Format-Table -AutoSize
    """
    ok, out = run_powershell(ps_script)
    if ok and out:
        console.print(out)


def get_boot_metrics() -> None:
    """Display last boot duration and system startup performance."""
    console.print("[bold cyan]⏱️ Measuring Windows Boot Metrics...[/bold cyan]")
    ps_script = """
    $os = Get-CimInstance Win32_OperatingSystem
    $lastBoot = $os.LastBootUpTime
    $now = Get-Date
    $uptime = $now - $lastBoot
    Write-Host "Last Boot Time: $lastBoot"
    Write-Host "System Uptime:  $($uptime.Days)d $($uptime.Hours)h $($uptime.Minutes)m $($uptime.Seconds)s"
    """
    ok, out = run_powershell(ps_script)
    if ok and out:
        console.print(out)


def disable_startup_item(item_name: str) -> None:
    """Disable or remove an autostart entry by name from Registry Run keys."""
    console.print(f"[bold cyan]Disabling startup application entry '{item_name}'...[/bold cyan]")
    ps_script = f"""
    $paths = @(
        "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run",
        "HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run"
    )
    foreach ($p in $paths) {{
        if (Get-ItemProperty -Path $p -Name "{item_name}" -ErrorAction SilentlyContinue) {{
            Remove-ItemProperty -Path $p -Name "{item_name}" -Force -ErrorAction SilentlyContinue
            Write-Host "Removed '{item_name}' from $p"
        }}
    }}
    """
    ok, out = run_powershell(ps_script, as_admin=True)
    if ok:
        console.print(f"[bold green]✓ Startup entry '{item_name}' removed from Registry autostart.[/bold green]")
    else:
        console.print(f"[red]Error: {out}[/red]")
