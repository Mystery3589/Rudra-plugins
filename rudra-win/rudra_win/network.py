"""Windows Network & Fast DNS Switcher Engine.

Lists network interfaces, tests latency, and switches DNS to Cloudflare, Google, AdGuard, or Quad9.
"""

from __future__ import annotations

from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rudra_win.core import run_powershell

console = Console()

DNS_PROVIDERS = {
    "cloudflare": ("1.1.1.1", "1.0.0.1"),
    "google": ("8.8.8.8", "8.8.4.4"),
    "adguard": ("94.140.14.14", "94.140.15.15"),
    "quad9": ("9.9.9.9", "149.112.112.112"),
}


def list_adapters() -> None:
    """List network adapters and current IP/DNS settings."""
    console.print(Panel.fit("[bold cyan]🌐 Network Adapters & Interfaces[/bold cyan]", border_style="cyan"))
    ps_script = """
    Get-NetAdapter | Select-Object Name, InterfaceDescription, Status, LinkSpeed, MacAddress | Format-Table -AutoSize
    """
    ok, out = run_powershell(ps_script)
    if ok and out:
        console.print(out)


def switch_dns(provider: str, adapter_name: Optional[str] = None) -> None:
    """Switch DNS servers to high-performance private providers (Cloudflare, Google, AdGuard, Quad9)."""
    p_lower = provider.lower()
    if p_lower == "dhcp" or p_lower == "auto":
        console.print("[bold cyan]Resetting DNS to Automatic (DHCP)...[/bold cyan]")
        ps_script = f"""
        $adapter = if ('{adapter_name}') {{ Get-NetAdapter -Name '{adapter_name}' }} else {{ Get-NetAdapter | Where-Object {{ $_.Status -eq 'Up' }} | Select-Object -First 1 }}
        Set-DnsClientServerAddress -InterfaceAlias $adapter.Name -ResetServerAddresses
        """
        ok, out = run_powershell(ps_script, as_admin=True)
        if ok:
            console.print("[bold green]✓ DNS reset to Automatic (DHCP).[/bold green]")
        return

    if p_lower not in DNS_PROVIDERS:
        console.print(f"[bold red]Unknown DNS provider '{provider}'. Choose: {', '.join(DNS_PROVIDERS.keys())}, dhcp[/bold red]")
        return

    primary, secondary = DNS_PROVIDERS[p_lower]
    console.print(f"[bold cyan]Switching DNS to {provider.upper()} ({primary}, {secondary})...[/bold cyan]")
    ps_script = f"""
    $adapter = if ('{adapter_name}') {{ Get-NetAdapter -Name '{adapter_name}' }} else {{ Get-NetAdapter | Where-Object {{ $_.Status -eq 'Up' }} | Select-Object -First 1 }}
    Set-DnsClientServerAddress -InterfaceAlias $adapter.Name -ServerAddresses @('{primary}', '{secondary}')
    Write-Host "Configured $($adapter.Name) to use {provider} DNS."
    """
    ok, out = run_powershell(ps_script, as_admin=True)
    if ok:
        console.print(f"[bold green]✓ DNS successfully switched to {provider.upper()}![/bold green]")
    else:
        console.print(f"[red]Error: {out}[/red]")
