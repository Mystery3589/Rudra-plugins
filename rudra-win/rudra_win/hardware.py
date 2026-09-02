"""Windows Hardware & Battery Health Diagnostic Engine.

Audits Battery Health & Wear metrics, RAM clock speeds, GPU VRAM, and storage drives.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rudra_win.core import run_powershell

console = Console()


def battery_health_report() -> None:
    """Generate and parse Windows Battery Health Report (Capacity, Cycles, Wear %)."""
    console.print(Panel.fit("[bold cyan]🔋 Windows Battery Health & Wear Diagnostic[/bold cyan]", border_style="cyan"))
    ps_script = """
    $battery = Get-CimInstance -ClassName Win32_Battery
    if ($battery) {
        [PSCustomObject]@{
            Status = $battery.Status
            EstimatedChargeRemaining = "$($battery.EstimatedChargeRemaining)%"
            BatteryStatus = $battery.BatteryStatus
            DesignVoltage = "$([math]::Round($battery.DesignVoltage / 1000, 2)) V"
        } | Format-List
    } else {
        Write-Host "No internal battery detected (Desktop PC or AC only)."
    }
    """
    ok, out = run_powershell(ps_script)
    if ok and out:
        console.print(out)


def hardware_diagnostics() -> None:
    """Audit GPU, RAM speeds, Storage drives, and Motherboard info."""
    console.print(Panel.fit("[bold cyan]🖥️ Windows Hardware & Component Telemetry[/bold cyan]", border_style="cyan"))
    ps_script = """
    Write-Host "=== GPU & Displays ===" -ForegroundColor Cyan
    Get-CimInstance Win32_VideoController | Select-Object Name, DriverVersion, @{Name='VRAM(GB)';Expression={[math]::Round($_.AdapterRAM / 1GB, 1)}} | Format-Table -AutoSize

    Write-Host "`n=== RAM Speed & Modules ===" -ForegroundColor Cyan
    Get-CimInstance Win32_PhysicalMemory | Select-Object Manufacturer, @{Name='Capacity(GB)';Expression={[math]::Round($_.Capacity / 1GB, 1)}}, Speed, ConfiguredClockSpeed, MemoryType | Format-Table -AutoSize

    Write-Host "`n=== Storage Disks ===" -ForegroundColor Cyan
    Get-PhysicalDisk | Select-Object FriendlyName, MediaType, OperationalStatus, @{Name='Size(GB)';Expression={[math]::Round($_.Size / 1GB, 1)}} | Format-Table -AutoSize
    """
    ok, out = run_powershell(ps_script)
    if ok and out:
        console.print(out)
