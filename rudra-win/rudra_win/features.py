"""Windows Features & Winget Presets Engine.

Manages optional Windows features (WSL2, Hyper-V, Sandbox) and installs 1-click curated software stacks.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rudra_win.core import run_powershell

console = Console()

PRESETS = {
    "dev": [
        ("Git", "Git.Git"),
        ("VSCode", "Microsoft.VisualStudioCode"),
        ("Windows Terminal", "Microsoft.WindowsTerminal"),
        ("PowerToys", "Microsoft.PowerToys"),
        ("NodeJS LTS", "OpenJS.NodeJS.LTS"),
        ("Python 3", "Python.Python.3.12"),
        ("7-Zip", "7zip.7zip"),
        ("Neovim", "Neovim.Neovim"),
    ],
    "gaming": [
        ("Steam", "Valve.Steam"),
        ("Discord", "Discord.Discord"),
        ("OBS Studio", "OBSProject.OBSStudio"),
        ("7-Zip", "7zip.7zip"),
        ("GeForce Experience / GPU app", "Nvidia.GeForceExperience"),
    ],
    "minimal": [
        ("7-Zip", "7zip.7zip"),
        ("VLC Media Player", "VideoLAN.VLC"),
        ("Brave Browser", "Brave.Brave"),
        ("PowerToys", "Microsoft.PowerToys"),
    ]
}


def toggle_windows_feature(feature: str, enable: bool = True) -> None:
    """Enable or disable an optional Windows feature (e.g. Microsoft-Windows-Subsystem-Linux, Containers-DisposableClientVM)."""
    state_cmd = "Enable-WindowsOptionalFeature -Online -All -NoRestart" if enable else "Disable-WindowsOptionalFeature -Online -NoRestart"
    console.print(f"[bold cyan]Modifying Windows Feature '{feature}' ({'Enabling' if enable else 'Disabling'})...[/bold cyan]")
    ps_script = f"{state_cmd} -FeatureName '{feature}'"
    ok, out = run_powershell(ps_script, as_admin=True)
    if ok:
        console.print(f"[bold green]✓ Feature '{feature}' successfully {'enabled' if enable else 'disabled'}![/bold green]")
    else:
        console.print(f"[red]Error: {out}[/red]")


def install_stack_preset(preset_name: str) -> None:
    """Install a curated winget application preset."""
    name_l = preset_name.lower()
    if name_l not in PRESETS:
        console.print(f"[bold red]Unknown preset '{preset_name}'. Choose: {', '.join(PRESETS.keys())}[/bold red]")
        return

    items = PRESETS[name_l]
    console.print(Panel.fit(f"[bold green]🚀 Deploying '{preset_name.upper()}' Software Stack[/bold green]\n[dim]Installing {len(items)} curated packages via Winget...[/dim]", border_style="green"))
    
    table = Table(title=f"Stack: {preset_name.capitalize()}")
    table.add_column("Application", style="bold cyan")
    table.add_column("Winget ID", style="dim")
    for app_name, app_id in items:
        table.add_row(app_name, app_id)
    console.print(table)
    
    ids = " ".join(f'"{app_id}"' for _, app_id in items)
    ps_script = f"""
    $ids = @({ids})
    foreach ($id in $ids) {{
        Write-Host "Installing $id..."
        winget install --id $id --silent --accept-source-agreements --accept-package-agreements
    }}
    """
    ok, out = run_powershell(ps_script)
    if ok:
        console.print(f"[bold green]✓ All packages from '{preset_name}' stack installed successfully![/bold green]")
    else:
        console.print(f"[yellow]Winget execution complete with notes: {out}[/yellow]")
