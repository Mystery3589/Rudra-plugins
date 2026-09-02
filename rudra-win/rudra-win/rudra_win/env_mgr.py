"""Windows Environment Variables & PATH Manager.

Safely append and remove directory paths from User and System PATH without length limits,
and manage persistent registry environment variables.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rudra_win.core import run_powershell

console = Console()


def list_environment_variables(scope: str = "User") -> None:
    """List persistent environment variables for User or Machine."""
    console.print(Panel.fit(f"[bold cyan]🌿 Windows Environment Variables ({scope.upper()})[/bold cyan]", border_style="cyan"))
    ps_script = f"""
    [System.Environment]::GetEnvironmentVariables('{scope}') | Format-Table -AutoSize
    """
    ok, out = run_powershell(ps_script)
    if ok and out:
        console.print(out)


def add_directory_to_path(dir_path: str, scope: str = "User") -> None:
    """Safely append directory to PATH in User or Machine scope."""
    console.print(f"[bold cyan]Adding '{dir_path}' to {scope} PATH...[/bold cyan]")
    ps_script = f"""
    $current = [System.Environment]::GetEnvironmentVariable('Path', '{scope}')
    $parts = $current -split ';' | Where-Object {{ $_ -ne '' }}
    if ($parts -notcontains '{dir_path}') {{
        $newPath = ($parts + '{dir_path}') -join ';'
        [System.Environment]::SetEnvironmentVariable('Path', $newPath, '{scope}')
        Write-Host "Added to {scope} PATH: {dir_path}"
    }} else {{
        Write-Host "Directory already exists on PATH."
    }}
    """
    as_admin = scope.lower() in ("machine", "system")
    ok, out = run_powershell(ps_script, as_admin=as_admin)
    if ok:
        console.print(f"[bold green]✓ '{dir_path}' appended to persistent {scope} PATH.[/bold green]")
    else:
        console.print(f"[red]Error: {out}[/red]")


def remove_directory_from_path(dir_path: str, scope: str = "User") -> None:
    """Remove directory from PATH in User or Machine scope."""
    console.print(f"[bold cyan]Removing '{dir_path}' from {scope} PATH...[/bold cyan]")
    ps_script = f"""
    $current = [System.Environment]::GetEnvironmentVariable('Path', '{scope}')
    $parts = $current -split ';' | Where-Object {{ $_ -ne '' -and $_ -ne '{dir_path}' }}
    $newPath = $parts -join ';'
    [System.Environment]::SetEnvironmentVariable('Path', $newPath, '{scope}')
    Write-Host "Updated {scope} PATH"
    """
    as_admin = scope.lower() in ("machine", "system")
    ok, out = run_powershell(ps_script, as_admin=as_admin)
    if ok:
        console.print(f"[bold green]✓ '{dir_path}' removed from {scope} PATH.[/bold green]")
    else:
        console.print(f"[red]Error: {out}[/red]")
