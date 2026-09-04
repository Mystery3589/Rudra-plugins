"""CLI interface for rudra-dotfiles ('rudra dotfiles' / 'rudra dot')."""

from __future__ import annotations

from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from rudra_dotfiles import manager, targets

console = Console()
app = typer.Typer(
    name="dotfiles",
    help="📦 Multi-profile dotfile manager & config switcher with auto-save.",
    no_args_is_help=True,
)


def _t():
    try:
        from rudra.theme import get_current_theme
        return get_current_theme()
    except Exception:
        from rudra.theme import ThemeConfig
        return ThemeConfig()


@app.command(name="list")
def list_cmd(
    target: Annotated[Optional[str], typer.Argument(help="Optional target to filter by (e.g. zsh, nvim).")] = None,
):
    """List all tracked dotfiles, their stored profiles, and the active profile."""
    th = _t()
    all_info = manager.list_profiles(target)

    # Filter to targets that have either profiles or live configs
    table = Table(
        title=f"[{th.table_header}]{th.prompt_char} Dotfile Profiles & Active Configurations[/{th.table_header}]",
        border_style=th.panel_border,
        show_lines=True,
    )
    table.add_column("Target", style=f"bold {th.primary}", no_wrap=True)
    table.add_column("Description / Path", style=th.dim)
    table.add_column("Active Profile", justify="center")
    table.add_column("Stored Profiles (Variants)", style=th.secondary)

    has_any = False
    for item in all_info:
        # Show all known targets or those with profiles
        profiles = item["profiles"]
        active = item["active_profile"]

        if active:
            active_str = f"[bold {th.success}]● {active}[/bold {th.success}]"
        else:
            active_str = f"[{th.dim}]system default[/{th.dim}]"

        prof_list = []
        for p in profiles:
            if p == active:
                prof_list.append(f"[bold {th.success}]{p} (active)[/bold {th.success}]")
            else:
                prof_list.append(p)

        profiles_str = ", ".join(prof_list) if prof_list else f"[{th.dim}]none (use 'save' to capture)[/{th.dim}]"
        table.add_row(
            item["target"],
            f"{item['label']}\n[{th.dim}]{item['system_path']}[/{th.dim}]",
            active_str,
            profiles_str,
        )
        if profiles or active:
            has_any = True

    console.print(table)
    if not has_any:
        console.print(f"\n[{th.dim}]To save your current config into a profile: [bold]rudra dotfiles save zsh default[/bold][/{th.dim}]")


@app.command(name="save")
def save_cmd(
    target: Annotated[str, typer.Argument(help="Dotfile target name (e.g. zsh, nvim, tmux).")],
    profile: Annotated[str, typer.Argument(help="Profile name to save as (e.g. default, minimal, work).")] = "default",
):
    """Save the current live system config into a profile."""
    th = _t()
    console.print(f"[{th.dim}]Capturing live config for '{target}' into profile '{profile}'...[/{th.dim}]")
    res = manager.save_current_config(target, profile)
    if res["success"]:
        console.print(
            f"[bold {th.success}]✓ Saved current '{target}' config into profile '[bold]{profile}[/bold]'![/bold {th.success}]\n"
            f"[{th.dim}]Source: {res['source']}\nStored: {res['stored_at']}[/{th.dim}]"
        )
    else:
        console.print(f"[bold {th.error}]✖ {res.get('error')}[/bold {th.error}]")
        raise typer.Exit(1)


@app.command(name="switch")
def switch_cmd(
    target: Annotated[str, typer.Argument(help="Dotfile target name (e.g. zsh, nvim, tmux).")],
    profile: Annotated[str, typer.Argument(help="Profile name to switch to.")],
):
    """Switch active profile with automatic safety backup of current live config."""
    th = _t()
    res = manager.switch_profile(target, profile)
    if res["success"]:
        backup_note = f"\n[{th.dim}]Safety backup created: [bold]{res['backup_id']}[/bold] (history)[/{th.dim}]" if res.get("backup_id") else ""
        console.print(
            Panel(
                f"[bold {th.success}]✓ Switched '{target}' to profile '[bold]{profile}[/bold]'![/bold {th.success}]\n"
                f"[{th.secondary}]Live path updated: {res['live_path']}[/{th.secondary}]"
                f"{backup_note}",
                title=f"[{th.primary}]{th.prompt_char} Profile Switch Activated[/{th.primary}]",
                border_style=th.panel_border,
            )
        )
    else:
        console.print(f"[bold {th.error}]✖ {res.get('error')}[/bold {th.error}]")
        raise typer.Exit(1)


@app.command(name="create")
def create_cmd(
    target: Annotated[str, typer.Argument(help="Dotfile target name.")],
    profile: Annotated[str, typer.Argument(help="New profile name.")],
):
    """Create a new blank or cloned profile for a target."""
    th = _t()
    res = manager.create_profile(target, profile)
    if res["success"]:
        console.print(f"[bold {th.success}]✓ Profile '{profile}' created for '{target}'![/bold {th.success}]")
        console.print(f"[{th.dim}]Path: {res['path']}[/{th.dim}]")
    else:
        console.print(f"[bold {th.error}]✖ {res.get('error')}[/bold {th.error}]")


@app.command(name="diff")
def diff_cmd(
    target: Annotated[str, typer.Argument(help="Dotfile target name.")],
    profile1: Annotated[str, typer.Argument(help="First profile name.")],
    profile2: Annotated[Optional[str], typer.Argument(help="Second profile name (leave empty to compare against live config).")] = None,
):
    """Compare two profiles, or compare a profile against the live system config."""
    th = _t()
    diff_text = manager.diff_profiles(target, profile1, profile2)
    if not diff_text:
        console.print(f"[bold {th.success}]✓ No differences found — configurations are identical.[/bold {th.success}]")
        return

    comp_label = f"profile:{profile1} vs profile:{profile2}" if profile2 else f"profile:{profile1} vs live system"
    console.print(f"[bold {th.primary}]{th.prompt_char} Diff ({comp_label}):[/bold {th.primary}]\n")
    syntax = Syntax(diff_text, "diff", theme="monokai", line_numbers=True)
    console.print(syntax)


@app.command(name="history")
def history_cmd(target: Annotated[str, typer.Argument(help="Dotfile target name.")]):
    """List historical safety backups created during profile switches."""
    th = _t()
    snaps = manager.list_history(target)
    if not snaps:
        console.print(f"[{th.warning}]No backup history found for '{target}'.[/{th.warning}]")
        return

    table = Table(
        title=f"[{th.table_header}]{th.prompt_char} Safety Backups for '{target}' ({len(snaps)})[/{th.table_header}]",
        border_style=th.panel_border,
    )
    table.add_column("Backup Timestamp ID", style=f"bold {th.primary}")
    table.add_column("Storage Path", style=th.dim)

    for s in snaps:
        table.add_row(s["timestamp"], s["path"])
    console.print(table)
    console.print(f"\n[{th.dim}]To restore a snapshot: [bold]rudra dotfiles restore {target} <timestamp_id>[/bold][/{th.dim}]")


@app.command(name="restore")
def restore_cmd(
    target: Annotated[str, typer.Argument(help="Dotfile target name.")],
    timestamp: Annotated[str, typer.Argument(help="Timestamp ID from 'rudra dotfiles history'.")],
):
    """Restore a historical safety backup to the live system."""
    th = _t()
    if manager.restore_backup(target, timestamp):
        console.print(f"[bold {th.success}]✓ Restored snapshot '{timestamp}' to live {target} config![/bold {th.success}]")
    else:
        console.print(f"[bold {th.error}]Failed to restore snapshot '{timestamp}'.[/{th.error}]")


@app.command(name="track")
def track_cmd(
    name: Annotated[str, typer.Argument(help="Unique name for the custom target (e.g. myapp).")],
    path: Annotated[str, typer.Option("--path", "-p", help="Path to config file or directory.")],
    label: Annotated[str, typer.Option("--label", "-l", help="Human-readable description.")] = "",
):
    """Register an arbitrary custom file or directory as a tracked dotfile target."""
    th = _t()
    entry = targets.register_custom_target(name, path, label)
    console.print(f"[bold {th.success}]✓ Registered custom target '{name}' pointing to {entry['path']}[/bold {th.success}]")
