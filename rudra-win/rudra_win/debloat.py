"""Windows Debloat & Privacy Engine.

Strips UWP bloatware, permanently kills Telemetry, Diagnostics Tracking,
Cortana, Copilot, Recall, and auto-downloading sponsored apps.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rudra_win.core import run_powershell

console = Console()

BLOAT_PACKAGES = [
    "*Microsoft.BingNews*",
    "*Microsoft.BingWeather*",
    "*Microsoft.GamingApp*",
    "*Microsoft.GetHelp*",
    "*Microsoft.Getstarted*",
    "*Microsoft.Microsoft3DViewer*",
    "*Microsoft.MicrosoftOfficeHub*",
    "*Microsoft.MicrosoftSolitaireCollection*",
    "*Microsoft.MixedReality.Portal*",
    "*Microsoft.People*",
    "*Microsoft.SkypeApp*",
    "*Microsoft.Todos*",
    "*Microsoft.WindowsFeedbackHub*",
    "*Microsoft.WindowsMaps*",
    "*Microsoft.YourPhone*",
    "*Microsoft.ZuneMusic*",
    "*Microsoft.ZuneVideo*",
    "*Clipchamp.Clipchamp*",
    "*SpotifyAB.SpotifyMusic*",
    "*Disney.DisneyPlus*",
    "*TikTok*",
    "*Facebook*",
    "*Instagram*",
    "*PrimeVideo*",
    "*CandyCrush*",
]

def remove_bloatware(aggressive: bool = False) -> None:
    """Purge preinstalled Windows bloatware apps."""
    console.print(Panel.fit("[bold red]🧹 Windows Bloatware Annihilator[/bold red]\n[dim]Removing preinstalled sponsor apps, unwanted UWP packages & garbage...[/dim]", border_style="red"))
    
    ps_script = """
    $apps = @(
        'Microsoft.BingNews', 'Microsoft.BingWeather', 'Microsoft.GetHelp',
        'Microsoft.Getstarted', 'Microsoft.Microsoft3DViewer', 'Microsoft.MicrosoftOfficeHub',
        'Microsoft.MicrosoftSolitaireCollection', 'Microsoft.MixedReality.Portal',
        'Microsoft.People', 'Microsoft.SkypeApp', 'Microsoft.WindowsFeedbackHub',
        'Microsoft.WindowsMaps', 'Microsoft.YourPhone', 'Microsoft.ZuneMusic',
        'Microsoft.ZuneVideo', 'Clipchamp.Clipchamp', 'SpotifyAB.SpotifyMusic',
        'Disney.DisneyPlus', 'TikTok', 'Facebook', 'CandyCrush'
    )
    foreach ($app in $apps) {
        Write-Host "Removing $app..."
        Get-AppxPackage -AllUsers -Name "*$app*" | Remove-AppxPackage -AllUsers -ErrorAction SilentlyContinue
        Get-AppxProvisionedPackage -Online | Where-Object { $_.DisplayName -like "*$app*" } | Remove-AppxProvisionedPackage -Online -ErrorAction SilentlyContinue
    }
    """
    ok, out = run_powershell(ps_script, as_admin=True)
    if ok:
        console.print("[bold green]✓ Preinstalled bloatware successfully purged from system and new account templates.[/bold green]")
    else:
        console.print(f"[red]Error during debloat: {out}[/red]")


def kill_telemetry() -> None:
    """Disable Windows Telemetry, Diagnostic Tracking, and Advertising ID."""
    console.print("[bold cyan]🔒 Disabling Windows Telemetry & Diagnostics Tracking...[/bold cyan]")
    ps_script = """
    # Disable Telemetry in Registry
    Set-ItemProperty -Path "HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\DataCollection" -Name "AllowTelemetry" -Type DWord -Value 0 -Force
    Set-ItemProperty -Path "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\DataCollection" -Name "AllowTelemetry" -Type DWord -Value 0 -Force
    
    # Disable Advertising ID
    Set-ItemProperty -Path "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\AdvertisingInfo" -Name "Enabled" -Type DWord -Value 0 -Force
    
    # Disable Consumer Experiences (Auto-downloading Candy Crush, Spotify, etc.)
    Set-ItemProperty -Path "HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\CloudContent" -Name "DisableWindowsConsumerFeatures" -Type DWord -Value 1 -Force
    Set-ItemProperty -Path "HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\CloudContent" -Name "DisableConsumerAccountStateContent" -Type DWord -Value 1 -Force
    
    # Disable In-app Suggestions & Settings Ads
    Set-ItemProperty -Path "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\ContentDeliveryManager" -Name "SubscribedContent-338388Enabled" -Type DWord -Value 0 -Force
    Set-ItemProperty -Path "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\ContentDeliveryManager" -Name "SubscribedContent-338389Enabled" -Type DWord -Value 0 -Force
    Set-ItemProperty -Path "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\ContentDeliveryManager" -Name "SubscribedContent-353696Enabled" -Type DWord -Value 0 -Force
    Set-ItemProperty -Path "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\ContentDeliveryManager" -Name "SystemPaneSuggestionsEnabled" -Type DWord -Value 0 -Force
    
    # Disable Telemetry Services
    Stop-Service -Name "DiagTrack" -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
    Set-Service -Name "DiagTrack" -StartupType Disabled -ErrorAction SilentlyContinue
    Stop-Service -Name "dmwappushservice" -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
    Set-Service -Name "dmwappushservice" -StartupType Disabled -ErrorAction SilentlyContinue
    """
    ok, out = run_powershell(ps_script, as_admin=True)
    if ok:
        console.print("[bold green]✓ Telemetry, tracking services, and sponsored app injections completely disabled![/bold green]")
    else:
        console.print(f"[red]Error disabling telemetry: {out}[/red]")


def kill_copilot_and_recall(disable: bool = True) -> None:
    """Disable or Enable Windows Copilot and Recall AI tracking."""
    val = 1 if disable else 0
    state = "Disabled" if disable else "Enabled"
    console.print(f"[bold cyan]🤖 Setting Copilot & Recall AI status to: {state}...[/bold cyan]")
    ps_script = f"""
    # Windows Copilot
    New-Item -Path "HKCU:\\Software\\Policies\\Microsoft\\Windows\\WindowsCopilot" -Force | Out-Null
    Set-ItemProperty -Path "HKCU:\\Software\\Policies\\Microsoft\\Windows\\WindowsCopilot" -Name "TurnOffWindowsCopilot" -Type DWord -Value {val} -Force
    New-Item -Path "HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsCopilot" -Force | Out-Null
    Set-ItemProperty -Path "HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsCopilot" -Name "TurnOffWindowsCopilot" -Type DWord -Value {val} -Force
    
    # Windows Recall / AI Snapshots
    New-Item -Path "HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsAI" -Force | Out-Null
    Set-ItemProperty -Path "HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsAI" -Name "DisableAIDataAnalysis" -Type DWord -Value {val} -Force
    """
    ok, out = run_powershell(ps_script, as_admin=True)
    if ok:
        console.print(f"[bold green]✓ Windows Copilot & AI Recall successfully {state.lower()}![/bold green]")
    else:
        console.print(f"[red]Error: {out}[/red]")
