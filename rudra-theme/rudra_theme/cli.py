"""CLI commands for rudra-theme plugin."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from rudra_theme.manager import (
    get_available_themes,
    get_current_theme,
    install_theme_from_source,
    render_theme_preview,
    reset_theme,
    set_active_theme,
)

console = Console()
app = typer.Typer(
    name="theme",
    help="Theme and visual styling customizer for Rudra.",
    no_args_is_help=False,
)


@app.callback(invoke_without_command=True)
def theme_main(ctx: typer.Context):
    """Browse or manage Rudra themes."""
    if ctx.invoked_subcommand is None:
        list_cmd()


@app.command(name="list")
def list_cmd():
    """List all available themes with color previews."""
    themes = get_available_themes()
    current = get_current_theme()

    table = Table(title="Available Rudra Themes", show_lines=True)
    table.add_column("Theme", style="bold", no_wrap=True)
    table.add_column("Palette Swatches", justify="left")
    table.add_column("Description", style="dim")
    table.add_column("Active", justify="center")

    for name, t in themes.items():
        is_active = (name == current.name)
        active_str = "[bold green]✓ ACTIVE[/bold green]" if is_active else "[dim]·[/dim]"
        theme_name_str = f"[{t.primary}]{t.name}[/{t.primary}]"
        if is_active:
            theme_name_str = f"[bold underline {t.primary}]{t.name}[/bold underline {t.primary}]"

        swatch = (
            f"[{t.primary}]■[/{t.primary}] "
            f"[{t.secondary}]■[/{t.secondary}] "
            f"[{t.accent}]■[/{t.accent}] "
            f"[{t.success}]■[/{t.success}] "
            f"[{t.warning}]■[/{t.warning}] "
            f"[{t.error}]■[/{t.error}]"
        )
        table.add_row(theme_name_str, swatch, t.description, active_str)

    console.print(table)
    console.print(f"\n[dim]To preview a theme:[/dim] [cyan]rudra theme preview <name>[/cyan]")
    console.print(f"[dim]To apply a theme:[/dim]   [bold cyan]rudra theme set <name>[/bold cyan]")


@app.command(name="preview")
def preview_cmd(
    name: Annotated[str, typer.Argument(help="Name of the theme to preview (e.g. cyberpunk, dracula, nord, matrix).")],
):
    """Render a full live preview of how a theme looks."""
    themes = get_available_themes()
    theme_key = name.lower().strip()
    if theme_key not in themes:
        console.print(f"[bold red]Theme '{name}' not found.[/bold red]")
        console.print(f"[dim]Run 'rudra theme list' to see all available themes.[/dim]")
        raise typer.Exit(1)

    theme = themes[theme_key]
    render_theme_preview(theme)
    console.print(f"[dim]To apply this theme, run:[/dim] [bold cyan]rudra theme set {theme.name}[/bold cyan]")


@app.command(name="set")
def set_cmd(
    name: Annotated[str, typer.Argument(help="Name of the theme to activate (e.g. cyberpunk, dracula, catppuccin, nord).")],
):
    """Set the active theme for all Rudra output."""
    if set_active_theme(name):
        current = get_current_theme()
        console.print(
            Panel.fit(
                f"[bold {current.success}]✓ Activated Theme: {current.label}[/bold {current.success}]\n"
                f"[{current.primary}]{current.description}[/{current.primary}]\n"
                f"[dim]Rudra outputs will now use the {current.name} palette.[/dim]",
                border_style=current.panel_border,
            )
        )
    else:
        console.print(f"[bold red]Theme '{name}' not found.[/bold red]")
        console.print(f"[dim]Run 'rudra theme list' to see available themes.[/dim]")
        raise typer.Exit(1)


@app.command(name="current")
def current_cmd():
    """Show the currently active theme."""
    current = get_current_theme()
    render_theme_preview(current)


@app.command(name="reset")
def reset_cmd():
    """Reset theme to default."""
    reset_theme()
    console.print("[bold green]✓ Theme reset to Rudra Classic default.[/bold green]")


@app.command(name="install")
def install_cmd(
    source: Annotated[str, typer.Argument(help="URL or local path to a standalone theme JSON file.")],
):
    """Download and install a single standalone theme file without downloading a whole bundle."""
    console.print(f"[bold cyan]Installing standalone theme from: {source}...[/bold cyan]")
    theme = install_theme_from_source(source)
    if theme:
        console.print(f"[bold green]✓ Theme '{theme.name}' installed successfully![/bold green]")
        render_theme_preview(theme)
        console.print(f"[dim]To activate it, run:[/dim] [bold cyan]rudra theme set {theme.name}[/bold cyan]")
    else:
        console.print(f"[bold red]Failed to install theme from {source}.[/bold red]")
        raise typer.Exit(1)


@app.command(name="export")
def export_cmd(
    name: Annotated[str, typer.Argument(help="Name of the theme to export.")],
    output: Annotated[Optional[Path], typer.Option("--output", "-o", help="Target output JSON file path.")] = None,
):
    """Export a theme to a standalone JSON file for sharing."""
    themes = get_available_themes()
    theme_key = name.lower().strip()
    if theme_key not in themes:
        console.print(f"[bold red]Theme '{name}' not found.[/bold red]")
        raise typer.Exit(1)

    theme = themes[theme_key]
    dest = output or (Path.cwd() / f"{theme.name}_theme.json")
    dest.write_text(json.dumps(theme.to_dict(), indent=2), encoding="utf-8")
    console.print(f"[bold green]✓ Theme '{theme.name}' exported to {dest}[/bold green]")
