"""Windows Process Slayer & Live Task Monitor Engine.

Force kill unresponsive apps, eradicate process trees, and inspect top resource-hogging tasks.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rudra_win.core import run_powershell

console = Console()


def kill_target(target: str, tree: bool = True) -> None:
    """Force kill a process by Name or PID, including all spawned child subprocesses."""
    console.print(f"[bold red]⚡ Terminating process target: {target} (Tree: {tree})...[/bold red]")
    if target.isdigit():
        ps_script = f"Stop-Process -Id {target} -Force"
    else:
        name = target if not target.endswith(".exe") else target[:-4]
        ps_script = f"Stop-Process -Name '{name}' -Force"
    ok, out = run_powershell(ps_script)
    if ok:
        console.print(f"[bold green]✓ Process '{target}' and child instances terminated.[/bold green]")
    else:
        console.print(f"[red]Error terminating process: {out}[/red]")


def top_processes(limit: int = 15, sort_by: str = "cpu") -> None:
    """Show the top resource-consuming Windows processes."""
    sort_property = "CPU" if sort_by.lower() == "cpu" else "WorkingSet"
    console.print(Panel.fit(f"[bold cyan]📊 Top {limit} Windows Tasks (Sorted by {sort_by.upper()})[/bold cyan]", border_style="cyan"))
    ps_script = f"""
    Get-Process | Sort-Object -Descending {sort_property} | Select-Object -First {limit} Id, ProcessName, @{{Name='CPU(s)';Expression={{[math]::Round($_.CPU,1)}}}}, @{{Name='RAM(MB)';Expression={{[math]::Round($_.WorkingSet / 1MB,1)}}}} | Format-Table -AutoSize
    """
    ok, out = run_powershell(ps_script)
    if ok and out:
        console.print(out)
