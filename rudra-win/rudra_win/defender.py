"""Windows Defender & Firewall Override Engine.

Controls real-time antivirus scanning, path exclusions, and firewall rules.
"""

from __future__ import annotations

from rich.console import Console
from rudra_win.core import run_powershell

console = Console()


def toggle_defender(enable: bool = True) -> None:
    """Turn Windows Defender Realtime Monitoring on or off."""
    disable_val = "$false" if enable else "$true"
    state_str = "Enabled" if enable else "Disabled"
    console.print(f"[bold cyan]🛡️ Setting Defender Realtime Monitoring to: {state_str}...[/bold cyan]")
    ps_script = f"Set-MpPreference -DisableRealtimeMonitoring {disable_val}"
    ok, out = run_powershell(ps_script, as_admin=True)
    if ok:
        console.print(f"[bold green]✓ Windows Defender Realtime Monitoring {state_str.lower()}![/bold green]")
    else:
        console.print(f"[red]Error: {out}[/red]")


def add_exclusion(target_path: str) -> None:
    """Add a folder or file to Windows Defender exclusion list."""
    console.print(f"[bold cyan]Adding exclusion path to Defender: {target_path}...[/bold cyan]")
    ps_script = f"Add-MpPreference -ExclusionPath '{target_path}'"
    ok, out = run_powershell(ps_script, as_admin=True)
    if ok:
        console.print(f"[bold green]✓ '{target_path}' excluded from Windows Defender scanning.[/bold green]")
    else:
        console.print(f"[red]Error: {out}[/red]")


def firewall_rule(port: int, action: str = "block", protocol: str = "TCP") -> None:
    """Create instant inbound firewall rule."""
    action_cap = "Block" if action.lower() == "block" else "Allow"
    rule_name = f"Rudra {action_cap} {protocol} {port}"
    console.print(f"[bold cyan]Creating Firewall rule '{rule_name}'...[/bold cyan]")
    ps_script = f"""
    New-NetFirewallRule -DisplayName '{rule_name}' -Direction Inbound -LocalPort {port} -Protocol {protocol} -Action {action_cap}
    """
    ok, out = run_powershell(ps_script, as_admin=True)
    if ok:
        console.print(f"[bold green]✓ Firewall rule created: {action_cap} port {port}/{protocol}![/bold green]")
    else:
        console.print(f"[red]Error: {out}[/red]")
