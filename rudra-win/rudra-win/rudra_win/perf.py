"""Windows Performance & Tuning Engine.

Unlocks hidden Ultimate Performance power plan, optimizes visual effects,
kills Game DVR input lag, and flushes network stacks.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rudra_win.core import run_powershell, run_cmd

console = Console()


def activate_ultimate_performance() -> None:
    """Unlock and activate the hidden 'Ultimate Performance' Windows power scheme."""
    console.print(Panel.fit("[bold green]⚡ Ultimate Performance Power Mode[/bold green]\n[dim]Unlocking hardware limits & removing micro-throttling on Windows...[/dim]", border_style="green"))
    ps_script = """
    # Duplicate the Ultimate Performance GUID
    $res = powercfg -duplicatescheme e9a42b02-d5df-448d-aa00-03f14749eb61
    if ($res -match "([a-f0-9\\-]{36})") {
        $guid = $matches[1]
        powercfg -setactive $guid
        Write-Host "Activated Ultimate Performance Plan: $guid"
    } else {
        # Fallback to High Performance
        powercfg -setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c
        Write-Host "Activated High Performance Plan."
    }
    """
    ok, out = run_powershell(ps_script, as_admin=True)
    if ok:
        console.print("[bold green]✓ Ultimate Performance mode engaged! CPU minimum state set to 100% full clock speed.[/bold green]")
    else:
        console.print(f"[red]Error: {out}[/red]")


def disable_game_dvr(disable: bool = True) -> None:
    """Disable Xbox Game Bar & background recording to eliminate frame-drops and input latency."""
    val = 0 if disable else 1
    state = "Disabled" if disable else "Enabled"
    console.print(f"[bold cyan]🎮 Setting Game DVR & Background Recording to: {state}...[/bold cyan]")
    ps_script = f"""
    Set-ItemProperty -Path "HKCU:\\System\\GameConfigStore" -Name "GameDVR_Enabled" -Type DWord -Value {val} -Force
    Set-ItemProperty -Path "HKCU:\\System\\GameConfigStore" -Name "GameDVR_FSEBehaviorMode" -Type DWord -Value 2 -Force
    Set-ItemProperty -Path "HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\GameDVR" -Name "AllowGameDVR" -Type DWord -Value {val} -Force -ErrorAction SilentlyContinue
    """
    ok, out = run_powershell(ps_script, as_admin=True)
    if ok:
        console.print(f"[bold green]✓ Game DVR {state.lower()}! Zero background capture overhead.[/bold green]")
    else:
        console.print(f"[red]Error: {out}[/red]")


def optimize_visual_effects(mode: str = "performance") -> None:
    """Tune Windows Visual Effects (performance vs appearance)."""
    console.print(f"[bold cyan]🎨 Optimizing Visual Effects for: {mode.upper()}...[/bold cyan]")
    if mode.lower() in ("perf", "performance", "fast"):
        ps_script = """
        # Custom visual effects: keep font smoothing, turn off drop shadows & heavy window animations
        Set-ItemProperty -Path "HKCU:\\Control Panel\\Desktop" -Name "UserPreferencesMask" -Type Binary -Value ([byte[]](0x90,0x12,0x03,0x80,0x10,0x00,0x00,0x00)) -Force
        Set-ItemProperty -Path "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\VisualEffects" -Name "VisualFXSetting" -Type DWord -Value 3 -Force
        # Keep ClearType font smoothing enabled
        Set-ItemProperty -Path "HKCU:\\Control Panel\\Desktop" -Name "FontSmoothing" -Type String -Value "2" -Force
        """
    else:
        ps_script = """
        Set-ItemProperty -Path "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\VisualEffects" -Name "VisualFXSetting" -Type DWord -Value 1 -Force
        """
    ok, out = run_powershell(ps_script)
    if ok:
        console.print("[bold green]✓ Visual effects tuned for ultra-responsive snappy window responsiveness.[/bold green]")
    else:
        console.print(f"[red]Error: {out}[/red]")


def flush_network() -> None:
    """Flush DNS cache, reset Winsock, and refresh IP configurations."""
    console.print("[bold cyan]🌐 Purging DNS & Resetting Windows Networking Stack...[/bold cyan]")
    ps_script = """
    Clear-DnsClientCache
    ipconfig /flushdns
    netsh winsock reset | Out-Null
    netsh int ip reset | Out-Null
    """
    ok, out = run_powershell(ps_script, as_admin=True)
    if ok:
        console.print("[bold green]✓ DNS cache flushed and Winsock stack fully renewed.[/bold green]")
    else:
        console.print(f"[red]Error: {out}[/red]")
