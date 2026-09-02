"""Windows Deep Disk & Cache Cleaner.

Purges temp folders, Prefetch, SoftwareDistribution Windows Update cache,
component stores, recycle bins, and event logs.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rudra_win.core import run_powershell

console = Console()


def clean_system_junk() -> None:
    """Deep clean all Windows caches, temporary directories, and recycle bins."""
    console.print(Panel.fit("[bold cyan]🧹 Windows Deep System Junk Cleaner[/bold cyan]\n[dim]Cleaning User Temp, Windows Temp, Prefetch, Update Cache & Recycle Bins...[/dim]", border_style="cyan"))
    
    ps_script = """
    $cleaned = 0
    
    # 1. User Temp
    $userTemp = [System.IO.Path]::GetTempPath()
    Get-ChildItem -Path $userTemp -Recurse -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    
    # 2. Windows Temp
    $winTemp = "C:\\Windows\\Temp"
    if (Test-Path $winTemp) {
        Get-ChildItem -Path $winTemp -Recurse -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    }
    
    # 3. Windows Prefetch
    $prefetch = "C:\\Windows\\Prefetch"
    if (Test-Path $prefetch) {
        Get-ChildItem -Path $prefetch -Force -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
    }
    
    # 4. Windows Update Download Cache
    $updateCache = "C:\\Windows\\SoftwareDistribution\\Download"
    if (Test-Path $updateCache) {
        Get-ChildItem -Path $updateCache -Recurse -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    }
    
    # 5. Recycle Bin
    Clear-RecycleBin -Force -ErrorAction SilentlyContinue
    """
    ok, out = run_powershell(ps_script, as_admin=True)
    if ok:
        console.print("[bold green]✓ Windows temporary caches, prefetch, and all Recycle Bins purged cleanly![/bold green]")
    else:
        console.print(f"[red]Error: {out}[/red]")


def clean_component_store() -> None:
    """Run DISM Component Store Cleanup to reclaim gigabytes of old Windows update leftovers."""
    console.print("[bold cyan]📦 Running DISM Component Store Cleanup (Reclaiming disk space)...[/bold cyan]")
    ps_script = "dism.exe /online /cleanup-image /startcomponentcleanup /resetbase"
    ok, out = run_powershell(ps_script, as_admin=True, timeout=300)
    if ok:
        console.print("[bold green]✓ Component store cleanup complete! Superfluous update backups reclaimed.[/bold green]")
    else:
        console.print(f"[red]DISM error: {out}[/red]")


def clear_event_logs() -> None:
    """Clear all Windows Event Viewer logs."""
    console.print("[bold cyan]📋 Clearing all Windows Event Viewer logs...[/bold cyan]")
    ps_script = "wevtutil el | ForEach-Object { wevtutil cl \"$_\" 2>$null }"
    ok, out = run_powershell(ps_script, as_admin=True)
    if ok:
        console.print("[bold green]✓ All Windows Event logs cleared.[/bold green]")
    else:
        console.print(f"[red]Error: {out}[/red]")
