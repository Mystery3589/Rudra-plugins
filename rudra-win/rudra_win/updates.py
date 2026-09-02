"""Windows Update Control Engine.

Pause updates for decades, eliminate forced unexpected reboots,
and force manual update installs directly from the command line.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from rich.console import Console
from rich.panel import Panel
from rudra_win.core import run_powershell

console = Console()


def pause_updates(years: int = 50) -> None:
    """Pause Windows Updates indefinitely (up to year 2099)."""
    future_date = (datetime.now() + timedelta(days=365 * years)).strftime("%Y-%m-%dT%H:%M:%SZ")
    console.print(Panel.fit(f"[bold yellow]⏸ Pausing Windows Updates until {future_date[:10]}[/bold yellow]\n[dim]No more unprompted background updates or surprise downloads...[/dim]", border_style="yellow"))
    
    ps_script = f"""
    $expiry = "{future_date}"
    $path = "HKLM:\\SOFTWARE\\Microsoft\\WindowsUpdate\\UX\\Settings"
    New-Item -Path $path -Force | Out-Null
    Set-ItemProperty -Path $path -Name "PauseFeatureUpdatesStartTime" -Type String -Value "2020-01-01T00:00:00Z" -Force
    Set-ItemProperty -Path $path -Name "PauseFeatureUpdatesEndTime" -Type String -Value $expiry -Force
    Set-ItemProperty -Path $path -Name "PauseQualityUpdatesStartTime" -Type String -Value "2020-01-01T00:00:00Z" -Force
    Set-ItemProperty -Path $path -Name "PauseQualityUpdatesEndTime" -Type String -Value $expiry -Force
    Set-ItemProperty -Path $path -Name "PauseUpdatesExpiryTime" -Type String -Value $expiry -Force
    """
    ok, out = run_powershell(ps_script, as_admin=True)
    if ok:
        console.print(f"[bold green]✓ Windows Updates successfully paused until {future_date[:10]}![/bold green]")
    else:
        console.print(f"[red]Error: {out}[/red]")


def unpause_updates() -> None:
    """Unpause and restore standard Windows update schedules."""
    console.print("[bold cyan]▶ Restoring Windows Update schedule...[/bold cyan]")
    ps_script = """
    $path = "HKLM:\\SOFTWARE\\Microsoft\\WindowsUpdate\\UX\\Settings"
    Remove-ItemProperty -Path $path -Name "PauseFeatureUpdatesStartTime" -ErrorAction SilentlyContinue
    Remove-ItemProperty -Path $path -Name "PauseFeatureUpdatesEndTime" -ErrorAction SilentlyContinue
    Remove-ItemProperty -Path $path -Name "PauseQualityUpdatesStartTime" -ErrorAction SilentlyContinue
    Remove-ItemProperty -Path $path -Name "PauseQualityUpdatesEndTime" -ErrorAction SilentlyContinue
    Remove-ItemProperty -Path $path -Name "PauseUpdatesExpiryTime" -ErrorAction SilentlyContinue
    """
    ok, out = run_powershell(ps_script, as_admin=True)
    if ok:
        console.print("[bold green]✓ Windows Update schedule unpaused and active.[/bold green]")
    else:
        console.print(f"[red]Error: {out}[/red]")


def block_forced_reboots() -> None:
    """Permanently prevent Windows Update from restarting PC while user is logged on."""
    console.print("[bold cyan]🛡️ Blocking forced Windows Update automatic reboots...[/bold cyan]")
    ps_script = """
    $path = "HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate\\AU"
    New-Item -Path $path -Force | Out-Null
    Set-ItemProperty -Path $path -Name "NoAutoRebootWithLoggedOnUsers" -Type DWord -Value 1 -Force
    Set-ItemProperty -Path $path -Name "AlwaysAutoRebootAtScheduledTime" -Type DWord -Value 0 -Force
    """
    ok, out = run_powershell(ps_script, as_admin=True)
    if ok:
        console.print("[bold green]✓ Windows will NEVER reboot your PC automatically while you are logged on.[/bold green]")
    else:
        console.print(f"[red]Error: {out}[/red]")


def install_updates_cli() -> None:
    """Trigger update search and install directly in terminal."""
    console.print("[bold cyan]🔍 Checking and installing pending Windows Updates...[/bold cyan]")
    ps_script = """
    if (-not (Get-Module -ListAvailable -Name PSWindowsUpdate)) {
        Install-PackageProvider -Name NuGet -MinimumVersion 2.8.5.201 -Force -Confirm:$false | Out-Null
        Install-Module PSWindowsUpdate -Force -Confirm:$false | Out-Null
    }
    Import-Module PSWindowsUpdate
    Get-WindowsUpdate -Install -AcceptAll -IgnoreReboot
    """
    ok, out = run_powershell(ps_script, as_admin=True, timeout=600)
    if ok:
        console.print("[bold green]✓ Windows updates evaluated and installed.[/bold green]")
    else:
        console.print(f"[yellow]PSWindowsUpdate note: {out}[/yellow]")
