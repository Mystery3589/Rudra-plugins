"""Windows Hosts File & Telemetry Blocklist Shield.

Manages DNS overrides in C:\\Windows\\System32\\drivers\\etc\\hosts to block domains
and neutralize telemetry hosts at the OS socket level.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rudra_win.core import run_powershell

console = Console()

TELEMETRY_DOMAINS = [
    "v10.events.data.microsoft.com",
    "v20.events.data.microsoft.com",
    "watson.telemetry.microsoft.com",
    "telemetry.microsoft.com",
    "telecommand.telemetry.microsoft.com",
    "feedback.microsoft.com",
    "feedback.search.microsoft.com",
    "activity.windows.com",
    "diagnostics.support.microsoft.com",
    "corpext.msitadfs.glbdns2.microsoft.com",
]


def list_hosts() -> None:
    """Display the active Windows hosts file entries."""
    console.print(Panel.fit("[bold cyan]📝 Windows Hosts File Entries (C:\\Windows\\System32\\drivers\\etc\\hosts)[/bold cyan]", border_style="cyan"))
    ps_script = r"""
    $hosts = "C:\Windows\System32\drivers\etc\hosts"
    Get-Content $hosts | Where-Object { $_ -notmatch '^\s*#' -and $_.Trim() -ne '' }
    """
    ok, out = run_powershell(ps_script)
    if ok and out:
        console.print(out)


def block_domain_in_hosts(domain: str) -> None:
    """Block a domain locally by redirecting it to 0.0.0.0 in hosts."""
    console.print(f"[bold cyan]Blocking domain '{domain}' in Windows hosts...[/bold cyan]")
    ps_script = f"""
    $hosts = "C:\\Windows\\System32\\drivers\\etc\\hosts"
    $entry = "0.0.0.0  {domain}"
    $content = Get-Content $hosts -Raw
    if ($content -notmatch [regex]::Escape('{domain}')) {{
        Add-Content -Path $hosts -Value "`n$entry" -Force
        Write-Host "Blocked $domain"
    }} else {{
        Write-Host "$domain is already in hosts file."
    }}
    """
    ok, out = run_powershell(ps_script, as_admin=True)
    if ok:
        console.print(f"[bold green]✓ Domain '{domain}' blocked via 0.0.0.0 loopback.[/bold green]")
    else:
        console.print(f"[red]Error: {out}[/red]")


def block_microsoft_telemetry_hosts() -> None:
    """Inject full Microsoft telemetry & tracking blocklist into Windows hosts file."""
    console.print(Panel.fit("[bold red]🛡️ Telemetry Host-Shield Activation[/bold red]\n[dim]Routing Microsoft diagnostic and telemetry endpoints to 0.0.0.0...[/dim]", border_style="red"))
    entries = "\\n".join(f"0.0.0.0  {d}" for d in TELEMETRY_DOMAINS)
    ps_script = f"""
    $hosts = "C:\\Windows\\System32\\drivers\\etc\\hosts"
    $domains = @({', '.join(f"'{d}'" for d in TELEMETRY_DOMAINS)})
    $content = Get-Content $hosts -Raw
    foreach ($d in $domains) {{
        if ($content -notmatch [regex]::Escape($d)) {{
            Add-Content -Path $hosts -Value "0.0.0.0  $d" -Force
        }}
    }}
    Write-Host "Injected telemetry blocklist."
    """
    ok, out = run_powershell(ps_script, as_admin=True)
    if ok:
        console.print(f"[bold green]✓ {len(TELEMETRY_DOMAINS)} telemetry endpoints blocked at OS socket level![/bold green]")
    else:
        console.print(f"[red]Error: {out}[/red]")
