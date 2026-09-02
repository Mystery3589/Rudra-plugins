"""WSL2 (Windows Subsystem for Linux) Power Management Engine.

Controls WSL2 instances, distros, memory allocation tuning via .wslconfig,
and RAM reclamation.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rudra_win.core import run_powershell

console = Console()


def wsl_status() -> None:
    """Show installed WSL distros, versions, and running status."""
    console.print(Panel.fit("[bold cyan]🐧 WSL2 Environment Status[/bold cyan]", border_style="cyan"))
    ps_script = """
    $distros = wsl --list --verbose
    Write-Output $distros
    """
    ok, out = run_powershell(ps_script)
    if ok and out:
        console.print(out)


def wsl_shutdown() -> None:
    """Instantly terminate all running WSL2 distributions to reclaim 100% of host RAM."""
    console.print("[bold yellow]⚡ Terminating all running WSL2 instances...[/bold yellow]")
    ps_script = "wsl --shutdown"
    ok, out = run_powershell(ps_script)
    if ok:
        console.print("[bold green]✓ All WSL2 virtual machines halted! Cached memory returned to Windows.[/bold green]")
    else:
        console.print(f"[red]Error: {out}[/red]")


def optimize_wsl_config(memory_gb: int = 8, processors: int = 4) -> None:
    """Generate or update optimized ~/.wslconfig on the Windows host."""
    console.print(f"[bold cyan]⚙️ Optimizing WSL2 configuration (Max RAM: {memory_gb}GB, Cores: {processors})...[/bold cyan]")
    ps_script = f"""
    $userProfile = [System.Environment]::GetFolderPath('UserProfile')
    $wslConfigPath = Join-Path $userProfile ".wslconfig"
    $configContent = @"
[wsl2]
memory={memory_gb}GB
processors={processors}
swap=4GB
localhostForwarding=true
nestedVirtualization=true
pageReporting=true
"@
    Set-Content -Path $wslConfigPath -Value $configContent -Force
    Write-Host "Created .wslconfig at $wslConfigPath"
    """
    ok, out = run_powershell(ps_script)
    if ok:
        console.print(f"[bold green]✓ .wslconfig generated with {memory_gb}GB RAM limit and {processors} CPU cores. Run 'rudra win wsl shutdown' to apply.[/bold green]")
    else:
        console.print(f"[red]Error: {out}[/red]")


def export_distro(distro: str, export_path: str) -> None:
    """Export a WSL distro to a standalone tar backup."""
    console.print(f"[bold cyan]📦 Exporting WSL distro '{distro}' to '{export_path}'...[/bold cyan]")
    ps_script = f"wsl --export '{distro}' '{export_path}'"
    ok, out = run_powershell(ps_script, timeout=600)
    if ok:
        console.print(f"[bold green]✓ Distro '{distro}' successfully exported to '{export_path}'![/bold green]")
    else:
        console.print(f"[red]Export error: {out}[/red]")
