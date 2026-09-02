"""Windows UI & Workflow Tweaks Engine.

Restores classic context menus, reveals hidden extensions, activates GodMode,
customizes taskbars, and controls dark mode.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rudra_win.core import run_powershell

console = Console()


def restart_explorer() -> None:
    """Instantly restart Windows Explorer to apply UI tweaks."""
    console.print("[dim]Restarting Windows Explorer...[/dim]")
    ps_script = "Stop-Process -Name explorer -Force; Start-Process explorer"
    run_powershell(ps_script, silent=True)


def set_classic_context_menu(enable: bool = True) -> None:
    """Restore classic Windows 10 context menu on Windows 11 (removes 'Show More Options')."""
    if enable:
        console.print("[bold cyan]✨ Enabling Classic Context Menu for Windows 11...[/bold cyan]")
        ps_script = """
        New-Item -Path "HKCU:\\Software\\Classes\\CLSID\\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}\\InprocServer32" -Value "" -Force | Out-Null
        """
    else:
        console.print("[bold cyan]Restoring Windows 11 Modern Context Menu...[/bold cyan]")
        ps_script = """
        Remove-Item -Path "HKCU:\\Software\\Classes\\CLSID\\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}" -Recurse -ErrorAction SilentlyContinue
        """
    ok, out = run_powershell(ps_script)
    if ok:
        restart_explorer()
        console.print(f"[bold green]✓ Context menu updated! (Classic menu {'Enabled' if enable else 'Disabled'})[/bold green]")
    else:
        console.print(f"[red]Error: {out}[/red]")


def optimize_file_explorer() -> None:
    """Show file extensions, show hidden files, open Explorer to 'This PC'."""
    console.print("[bold cyan]📂 Configuring Power-User File Explorer defaults...[/bold cyan]")
    ps_script = """
    # Show File Extensions
    Set-ItemProperty -Path "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced" -Name "HideFileExt" -Type DWord -Value 0 -Force
    # Show Hidden Files
    Set-ItemProperty -Path "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced" -Name "Hidden" -Type DWord -Value 1 -Force
    # Open File Explorer to 'This PC' instead of 'Quick Access / Home'
    Set-ItemProperty -Path "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced" -Name "LaunchTo" -Type DWord -Value 1 -Force
    # Hide Recent Files in Quick Access
    Set-ItemProperty -Path "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer" -Name "ShowRecent" -Type DWord -Value 0 -Force
    Set-ItemProperty -Path "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer" -Name "ShowFrequent" -Type DWord -Value 0 -Force
    """
    ok, out = run_powershell(ps_script)
    if ok:
        restart_explorer()
        console.print("[bold green]✓ File Explorer configured (Extensions shown, Hidden files visible, Opens to 'This PC')![/bold green]")
    else:
        console.print(f"[red]Error: {out}[/red]")


def create_godmode_folder() -> None:
    """Create GodMode Master Control Panel on the user Desktop."""
    console.print("[bold yellow]⚡ Creating GodMode Master Control Panel folder on Desktop...[/bold yellow]")
    ps_script = """
    $desktop = [Environment]::GetFolderPath('Desktop')
    $path = Join-Path $desktop "GodMode.{ED7BA470-8E54-465E-825C-99712043E01C}"
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path | Out-Null
        Write-Host "Created GodMode folder."
    }
    """
    ok, out = run_powershell(ps_script)
    if ok:
        console.print("[bold green]✓ GodMode folder created on your Desktop! Access 200+ advanced Windows control panel tools in 1 place.[/bold green]")
    else:
        console.print(f"[red]Error: {out}[/red]")


def set_taskbar_alignment(alignment: str = "left") -> None:
    """Set Windows 11 taskbar alignment to 'left' or 'center'."""
    val = 0 if alignment.lower() == "left" else 1
    console.print(f"[bold cyan]Aligning Taskbar to: {alignment.upper()}...[/bold cyan]")
    ps_script = f"""
    Set-ItemProperty -Path "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced" -Name "TaskbarAl" -Type DWord -Value {val} -Force
    """
    ok, out = run_powershell(ps_script)
    if ok:
        console.print(f"[bold green]✓ Taskbar alignment set to {alignment.lower()}![/bold green]")
    else:
        console.print(f"[red]Error: {out}[/red]")


def set_dark_mode(enable: bool = True) -> None:
    """Toggle System and Apps Dark Mode."""
    val = 0 if enable else 1
    state = "Dark Mode" if enable else "Light Mode"
    console.print(f"[bold cyan]Switching Windows to: {state}...[/bold cyan]")
    ps_script = f"""
    Set-ItemProperty -Path "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize" -Name "AppsUseLightTheme" -Type DWord -Value {val} -Force
    Set-ItemProperty -Path "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize" -Name "SystemUsesLightTheme" -Type DWord -Value {val} -Force
    """
    ok, out = run_powershell(ps_script)
    if ok:
        console.print(f"[bold green]✓ {state} applied instantly![/bold green]")
    else:
        console.print(f"[red]Error: {out}[/red]")


def disable_start_menu_bing() -> None:
    """Kill Bing web search results and suggestions inside the Start Menu search box."""
    console.print("[bold cyan]🚫 Disabling Bing web search in Start Menu...[/bold cyan]")
    ps_script = """
    Set-ItemProperty -Path "HKCU:\\Software\\Policies\\Microsoft\\Windows\\Explorer" -Name "DisableSearchBoxSuggestions" -Type DWord -Value 1 -Force
    Set-ItemProperty -Path "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Search" -Name "BingSearchEnabled" -Type DWord -Value 0 -Force
    Set-ItemProperty -Path "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Search" -Name "CortanaConsent" -Type DWord -Value 0 -Force
    """
    ok, out = run_powershell(ps_script)
    if ok:
        console.print("[bold green]✓ Start Menu search is now 100% local and lightning fast (No Bing clutter).[/bold green]")
    else:
        console.print(f"[red]Error: {out}[/red]")
