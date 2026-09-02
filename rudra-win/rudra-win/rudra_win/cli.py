"""Rudra Windows Power Tools CLI Command Center.

Bend Windows according to your will: debloat, tweak UI, unleash ultimate performance,
pause updates indefinitely, clean deep system junk, override Defender, control WSL2,
manage startup autoruns, services, process trees, hosts adblocking, and repair system integrity.
"""

from __future__ import annotations

import typer
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from rudra_win.debloat import remove_bloatware, kill_telemetry, kill_copilot_and_recall
from rudra_win.tweaks import (
    set_classic_context_menu,
    optimize_file_explorer,
    create_godmode_folder,
    set_taskbar_alignment,
    set_dark_mode,
    disable_start_menu_bing,
    restart_explorer,
)
from rudra_win.perf import (
    activate_ultimate_performance,
    disable_game_dvr,
    optimize_visual_effects,
    flush_network,
)
from rudra_win.clean import clean_system_junk, clean_component_store, clear_event_logs
from rudra_win.updates import (
    pause_updates,
    unpause_updates,
    block_forced_reboots,
    install_updates_cli,
)
from rudra_win.defender import toggle_defender, add_exclusion, firewall_rule
from rudra_win.features import toggle_windows_feature, install_stack_preset
from rudra_win.wsl import wsl_status, wsl_shutdown, optimize_wsl_config, export_distro
from rudra_win.startup import list_startup_items, get_boot_metrics, disable_startup_item
from rudra_win.services import list_services_cli, control_service, enable_gaming_mode_services
from rudra_win.process import kill_target, top_processes
from rudra_win.env_mgr import list_environment_variables, add_directory_to_path, remove_directory_from_path
from rudra_win.hosts import list_hosts, block_domain_in_hosts, block_microsoft_telemetry_hosts
from rudra_win.repair import run_sfc_scan, run_dism_health_restore, auto_system_recovery
from rudra_win.hardware import battery_health_report, hardware_diagnostics
from rudra_win.network import list_adapters, switch_dns
from rudra_win.core import run_powershell, IS_WINDOWS

app = typer.Typer(
    name="win",
    help="⚡ Windows Overlord & Power Tools — Debloat, UI tweaks, Ultimate Performance, Updates, Cleaning, Defender, WSL, Services & Repairs.",
    no_args_is_help=True,
)

# Sub-command groups
perf_app = typer.Typer(name="perf", help="Performance optimizations, power schemes & latency tuning.", no_args_is_help=True)
clean_app = typer.Typer(name="clean", help="Deep system cleaning, caches & DISM component stores.", no_args_is_help=True)
update_app = typer.Typer(name="update", help="Windows update control, pauses & reboot blocks.", no_args_is_help=True)
tweak_app = typer.Typer(name="tweak", help="Windows UI, context menus & Explorer customizer.", no_args_is_help=True)
wsl_app = typer.Typer(name="wsl", help="WSL2 environment manager, memory limits & distro export.", no_args_is_help=True)
startup_app = typer.Typer(name="startup", help="Startup apps manager & boot time analysis.", no_args_is_help=True)
services_app = typer.Typer(name="services", help="Background services manager & gaming throughput mode.", no_args_is_help=True)
env_app = typer.Typer(name="env", help="Environment variables & PATH manager.", no_args_is_help=True)
hosts_app = typer.Typer(name="hosts", help="Hosts file management & telemetry blocklist shield.", no_args_is_help=True)
repair_app = typer.Typer(name="repair", help="System integrity repairs (SFC, DISM, automated recovery).", no_args_is_help=True)
net_app = typer.Typer(name="net", help="Network adapters, latency & fast DNS switcher.", no_args_is_help=True)

app.add_typer(perf_app, name="perf")
app.add_typer(clean_app, name="clean")
app.add_typer(update_app, name="update")
app.add_typer(tweak_app, name="tweak")
app.add_typer(wsl_app, name="wsl")
app.add_typer(startup_app, name="startup")
app.add_typer(services_app, name="services")
app.add_typer(env_app, name="env")
app.add_typer(hosts_app, name="hosts")
app.add_typer(repair_app, name="repair")
app.add_typer(net_app, name="net")

console = Console()


# ── Top-Level Commands ────────────────────────────────────────────────────────

@app.command(name="info")
def win_info():
    """Display Windows build, hardware stats, power state, and active optimizations."""
    console.print(Panel.fit("[bold cyan]🪟 Windows System Diagnostic & Control Dashboard[/bold cyan]", border_style="cyan"))
    ps_script = """
    $os = Get-CimInstance Win32_OperatingSystem
    $cs = Get-CimInstance Win32_ComputerSystem
    $cpu = Get-CimInstance Win32_Processor
    [PSCustomObject]@{
        OS = $os.Caption
        Version = $os.Version
        Build = $os.BuildNumber
        Uptime = (New-TimeSpan -Start $os.LastBootUpTime -End (Get-Date)).ToString("d'd 'h'h 'm'm'")
        RAM = [math]::Round($cs.TotalPhysicalMemory / 1GB, 1).ToString() + " GB"
        CPU = $cpu.Name
    } | Format-List
    """
    ok, out = run_powershell(ps_script)
    if ok and out:
        console.print(out)


@app.command(name="debloat")
def debloat_cmd(
    aggressive: bool = typer.Option(False, "--aggressive", "-a", help="Aggressive removal of all non-essential UWP packages"),
):
    """Purge preinstalled Windows bloatware apps (Xbox, Weather, News, Candy Crush, etc.)."""
    remove_bloatware(aggressive=aggressive)


@app.command(name="privacy")
def privacy_cmd():
    """Disable Windows Telemetry, Diagnostic Tracking, Advertising ID, and auto-downloaded sponsors."""
    kill_telemetry()


@app.command(name="copilot")
def copilot_cmd(
    state: str = typer.Argument("off", help="'off' to kill Copilot & Recall AI, 'on' to restore"),
):
    """Toggle Windows Copilot and Recall AI tracking on or off."""
    disable = state.lower() in ("off", "disable", "kill", "0")
    kill_copilot_and_recall(disable=disable)


@app.command(name="godmode")
def godmode_cmd():
    """Create the GodMode Master Control Panel folder on your Desktop."""
    create_godmode_folder()


@app.command(name="classic-menu")
def classic_menu_cmd(
    state: str = typer.Argument("on", help="'on' for classic Windows 10 menu on Win11, 'off' for standard Win11 menu"),
):
    """Restore Windows 10 classic right-click context menu on Windows 11."""
    enable = state.lower() in ("on", "enable", "classic", "1")
    set_classic_context_menu(enable=enable)


@app.command(name="explorer")
def explorer_cmd():
    """Optimize File Explorer: Show file extensions, reveal hidden files, open to 'This PC'."""
    optimize_file_explorer()


@app.command(name="dark-mode")
def dark_mode_cmd(
    state: str = typer.Argument("on", help="'on' for Dark Mode, 'off' for Light Mode"),
):
    """Toggle Dark Mode across Windows Apps and System."""
    enable = state.lower() in ("on", "enable", "dark", "1")
    set_dark_mode(enable=enable)


@app.command(name="taskbar")
def taskbar_cmd(
    alignment: str = typer.Argument("left", help="Alignment: 'left' or 'center'"),
):
    """Set Windows 11 Taskbar alignment to left or center."""
    set_taskbar_alignment(alignment=alignment)


@app.command(name="defender")
def defender_cmd(
    state: str = typer.Argument(..., help="'on', 'off', or 'exclude'"),
    path: Optional[str] = typer.Option(None, "--path", "-p", help="Target folder/file path to exclude"),
):
    """Control Windows Defender Realtime Monitoring or add exclusions."""
    if state.lower() == "exclude":
        if not path:
            console.print("[bold red]Please provide --path to exclude from Defender.[/bold red]")
            raise typer.Exit(1)
        add_exclusion(path)
    else:
        enable = state.lower() in ("on", "enable", "1")
        toggle_defender(enable=enable)


@app.command(name="firewall")
def firewall_cmd(
    action: str = typer.Argument(..., help="'block' or 'allow'"),
    port: int = typer.Argument(..., help="Port number (e.g. 8080)"),
    protocol: str = typer.Option("TCP", "--protocol", "-p", help="Protocol: TCP or UDP"),
):
    """Add instant inbound firewall rule to block or allow a port."""
    firewall_rule(port=port, action=action, protocol=protocol)


@app.command(name="kill")
def kill_cmd(
    target: str = typer.Argument(..., help="Process Name (e.g. chrome, discord) or Process ID"),
    tree: bool = typer.Option(True, "--tree/--single", help="Kill entire child process tree"),
):
    """Force terminate stubborn or unresponsive Windows processes."""
    kill_target(target=target, tree=tree)


@app.command(name="top")
def top_cmd(
    limit: int = typer.Option(15, "--limit", "-n", help="Number of processes to display"),
    sort_by: str = typer.Option("cpu", "--sort", "-s", help="Sort by: 'cpu' or 'ram'"),
):
    """Live monitor of top resource-consuming Windows tasks."""
    top_processes(limit=limit, sort_by=sort_by)


@app.command(name="battery")
def battery_cmd():
    """Display Windows Battery Health, capacity and charge status."""
    battery_health_report()


@app.command(name="hardware")
def hardware_cmd():
    """Display detailed GPU VRAM, RAM clock speeds, and storage drive health."""
    hardware_diagnostics()


@app.command(name="preset")
def preset_cmd(
    name: str = typer.Argument("dev", help="Preset name: 'dev', 'gaming', or 'minimal'"),
):
    """Install 1-click curated application stacks via Winget."""
    install_stack_preset(name)


@app.command(name="power")
def power_cmd(
    action: str = typer.Argument(..., help="Action: 'sleep', 'hibernate', 'restart', 'shutdown', or 'lock'"),
):
    """Control Windows power state instantly."""
    action_l = action.lower()
    console.print(f"[bold yellow]Executing Windows Power Action: {action.upper()}...[/bold yellow]")
    if action_l == "lock":
        ps_script = "rundll32.exe user32.dll,LockWorkStation"
    elif action_l == "sleep":
        ps_script = "rundll32.exe powrprof.dll,SetSuspendState 0,1,0"
    elif action_l == "hibernate":
        ps_script = "shutdown.exe /h"
    elif action_l == "restart":
        ps_script = "shutdown.exe /r /t 0"
    elif action_l == "shutdown":
        ps_script = "shutdown.exe /s /t 0"
    else:
        console.print(f"[bold red]Unknown power action '{action}'. Choose: sleep, hibernate, restart, shutdown, lock[/bold red]")
        return
    run_powershell(ps_script)


# ── Performance Sub-commands ──────────────────────────────────────────────────

@perf_app.command(name="ultimate-plan")
def perf_ultimate_plan():
    """Unlock and engage the hidden 'Ultimate Performance' Windows power scheme."""
    activate_ultimate_performance()


@perf_app.command(name="game-dvr")
def perf_game_dvr(
    state: str = typer.Argument("off", help="'off' to disable input-lagging Game DVR, 'on' to enable"),
):
    """Disable Xbox Game DVR background recording to eliminate latency."""
    disable = state.lower() in ("off", "disable", "kill", "0")
    disable_game_dvr(disable=disable)


@perf_app.command(name="visuals")
def perf_visuals(
    mode: str = typer.Argument("perf", help="'perf' (fastest window responsiveness) or 'appearance'"),
):
    """Tune Windows visual animation effects."""
    optimize_visual_effects(mode=mode)


@perf_app.command(name="flush-dns")
def perf_flush_dns():
    """Flush DNS cache and renew Winsock TCP/IP stack."""
    flush_network()


# ── Clean Sub-commands ────────────────────────────────────────────────────────

@clean_app.command(name="all")
def clean_all_cmd():
    """Deep clean all Windows temp caches, Prefetch, and Recycle Bins."""
    clean_system_junk()


@clean_app.command(name="component-store")
def clean_component_store_cmd():
    """Run DISM Component Store cleanup to reclaim update storage space."""
    clean_component_store()


@clean_app.command(name="logs")
def clean_logs_cmd():
    """Clear all Windows Event Viewer logs."""
    clear_event_logs()


# ── Update Sub-commands ───────────────────────────────────────────────────────

@update_app.command(name="pause")
def update_pause_cmd(
    years: int = typer.Option(50, "--years", "-y", help="Years to pause updates for (default: 50 years)"),
):
    """Pause Windows updates indefinitely (up to year 2099)."""
    pause_updates(years=years)


@update_app.command(name="unpause")
def update_unpause_cmd():
    """Restore normal Windows update schedules."""
    unpause_updates()


@update_app.command(name="block-reboot")
def update_block_reboot_cmd():
    """Prevent Windows from restarting your PC while you are logged on."""
    block_forced_reboots()


@update_app.command(name="install")
def update_install_cmd():
    """Force check and install pending Windows updates directly in terminal."""
    install_updates_cli()


# ── WSL2 Sub-commands ─────────────────────────────────────────────────────────

@wsl_app.command(name="status")
def wsl_status_cmd():
    """List installed WSL distros, versions, and running state."""
    wsl_status()


@wsl_app.command(name="shutdown")
def wsl_shutdown_cmd():
    """Terminate all running WSL2 virtual machines to free 100% of host RAM."""
    wsl_shutdown()


@wsl_app.command(name="config")
def wsl_config_cmd(
    memory: int = typer.Option(8, "--memory", "-m", help="Max RAM allocation in GB"),
    cores: int = typer.Option(4, "--cores", "-c", help="Max CPU cores allocation"),
):
    """Generate tuned .wslconfig memory and CPU caps."""
    optimize_wsl_config(memory_gb=memory, processors=cores)


@wsl_app.command(name="export")
def wsl_export_cmd(
    distro: str = typer.Argument(..., help="Distro name (e.g. Ubuntu)"),
    path: str = typer.Argument(..., help="Destination tar file path"),
):
    """Export WSL distro to a standalone tar snapshot."""
    export_distro(distro=distro, export_path=path)


# ── Startup Sub-commands ──────────────────────────────────────────────────────

@startup_app.command(name="list")
def startup_list_cmd():
    """List all applications configured to launch at Windows startup."""
    list_startup_items()


@startup_app.command(name="boot-time")
def startup_boot_time_cmd():
    """Measure last boot duration and system startup metrics."""
    get_boot_metrics()


@startup_app.command(name="disable")
def startup_disable_cmd(
    name: str = typer.Argument(..., help="Application name in startup registry"),
):
    """Disable/remove an autostart application."""
    disable_startup_item(name)


# ── Services Sub-commands ─────────────────────────────────────────────────────

@services_app.command(name="list")
def services_list_cmd(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Filter services by name"),
):
    """List Windows background services."""
    list_services_cli(search=search)


@services_app.command(name="control")
def services_control_cmd(
    name: str = typer.Argument(..., help="Service name (e.g. Spooler, DiagTrack)"),
    action: str = typer.Argument(..., help="Action: 'start', 'stop', 'restart', 'disable', 'enable'"),
):
    """Start, stop, restart, disable, or enable a service."""
    control_service(name=name, action=action)


@services_app.command(name="gaming-mode")
def services_gaming_mode_cmd():
    """Temporarily stop non-critical background services for maximum gaming/compile throughput."""
    enable_gaming_mode_services()


# ── Environment Variables Sub-commands ────────────────────────────────────────

@env_app.command(name="list")
def env_list_cmd(
    scope: str = typer.Option("User", "--scope", "-s", help="'User' or 'Machine'"),
):
    """List persistent environment variables."""
    list_environment_variables(scope=scope)


@env_app.command(name="add-path")
def env_add_path_cmd(
    path: str = typer.Argument(..., help="Directory path to append to PATH"),
    scope: str = typer.Option("User", "--scope", "-s", help="'User' or 'Machine'"),
):
    """Safely append directory to persistent PATH without length limits."""
    add_directory_to_path(dir_path=path, scope=scope)


@env_app.command(name="remove-path")
def env_remove_path_cmd(
    path: str = typer.Argument(..., help="Directory path to remove from PATH"),
    scope: str = typer.Option("User", "--scope", "-s", help="'User' or 'Machine'"),
):
    """Remove directory from persistent PATH."""
    remove_directory_from_path(dir_path=path, scope=scope)


# ── Hosts Shield Sub-commands ─────────────────────────────────────────────────

@hosts_app.command(name="list")
def hosts_list_cmd():
    """View active Windows hosts file overrides."""
    list_hosts()


@hosts_app.command(name="block")
def hosts_block_cmd(
    domain: str = typer.Argument(..., help="Domain name to block (e.g. telemetry.example.com)"),
):
    """Block domain locally by redirecting to 0.0.0.0."""
    block_domain_in_hosts(domain=domain)


@hosts_app.command(name="block-telemetry")
def hosts_block_telemetry_cmd():
    """Inject full Microsoft telemetry & tracking blocklist into hosts file."""
    block_microsoft_telemetry_hosts()


# ── Repair Sub-commands ───────────────────────────────────────────────────────

@repair_app.command(name="sfc")
def repair_sfc_cmd():
    """Run SFC System File Checker scan."""
    run_sfc_scan()


@repair_app.command(name="dism")
def repair_dism_cmd():
    """Run DISM online image health restoration."""
    run_dism_health_restore()


@repair_app.command(name="auto")
def repair_auto_cmd():
    """Execute full 3-stage automated Windows recovery sequence."""
    auto_system_recovery()


# ── Network Sub-commands ──────────────────────────────────────────────────────

@net_app.command(name="adapters")
def net_adapters_cmd():
    """List network adapters and current link speeds."""
    list_adapters()


@net_app.command(name="set-dns")
def net_set_dns_cmd(
    provider: str = typer.Argument(..., help="Provider: 'cloudflare', 'google', 'adguard', 'quad9', 'dhcp'"),
    adapter: Optional[str] = typer.Option(None, "--adapter", "-a", help="Specific network adapter name"),
):
    """Switch DNS servers to high-performance private providers."""
    switch_dns(provider=provider, adapter_name=adapter)
