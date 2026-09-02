"""Theme manager and single-theme installer for Rudra."""

from __future__ import annotations

import json
import shutil
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from rudra_theme.themes import BUILTIN_THEMES, ThemePalette

THEMES_DIR = Path.home() / ".rudra" / "themes"
ACTIVE_THEME_FILE = Path.home() / ".rudra" / "theme.json"

console = Console()


def get_available_themes() -> dict[str, ThemePalette]:
    """Return all built-in and user-installed standalone themes."""
    themes = dict(BUILTIN_THEMES)
    THEMES_DIR.mkdir(parents=True, exist_ok=True)

    # Load any single-file custom themes downloaded into ~/.rudra/themes/
    for file in THEMES_DIR.glob("*.json"):
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
            name = data.get("name", file.stem)
            themes[name] = ThemePalette(**data)
        except Exception:
            pass

    return themes


def get_current_theme() -> ThemePalette:
    """Read the currently active theme or default."""
    if ACTIVE_THEME_FILE.exists():
        try:
            data = json.loads(ACTIVE_THEME_FILE.read_text(encoding="utf-8"))
            theme_name = data.get("name", "default")
            all_themes = get_available_themes()
            if theme_name in all_themes:
                return all_themes[theme_name]
        except Exception:
            pass
    return BUILTIN_THEMES["default"]


def set_active_theme(theme_name: str) -> bool:
    """Set the active theme."""
    all_themes = get_available_themes()
    name = theme_name.lower().strip()
    if name not in all_themes:
        return False

    theme = all_themes[name]
    ACTIVE_THEME_FILE.parent.mkdir(parents=True, exist_ok=True)
    ACTIVE_THEME_FILE.write_text(json.dumps(theme.to_dict(), indent=2), encoding="utf-8")
    return True


def reset_theme() -> None:
    """Reset theme to default."""
    ACTIVE_THEME_FILE.unlink(missing_ok=True)


def install_theme_from_source(source: str) -> Optional[ThemePalette]:
    """Download and install a single theme JSON file from a URL or local path."""
    THEMES_DIR.mkdir(parents=True, exist_ok=True)
    data_str = ""

    # Check if local path
    local_path = Path(source).expanduser()
    if local_path.is_file():
        data_str = local_path.read_text(encoding="utf-8")
    elif source.startswith("http://") or source.startswith("https://"):
        req = urllib.request.Request(source, headers={"User-Agent": "rudra/0.1"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data_str = resp.read().decode("utf-8")
        except Exception as e:
            console.print(f"[bold red]Failed to download theme from {source}: {e}[/bold red]")
            return None
    else:
        console.print(f"[bold red]Invalid theme source (must be a local file path or http/https URL).[/bold red]")
        return None

    try:
        data = json.loads(data_str)
        theme = ThemePalette(**data)
        dest = THEMES_DIR / f"{theme.name}.json"
        dest.write_text(json.dumps(theme.to_dict(), indent=2), encoding="utf-8")
        return theme
    except Exception as e:
        console.print(f"[bold red]Invalid theme definition format: {e}[/bold red]")
        return None


def render_theme_preview(theme: ThemePalette) -> None:
    """Render an aesthetic live preview of a theme palette."""
    t = theme

    # 1. Header Banner
    banner_text = Text()
    banner_text.append(f" {t.prompt_char} RUDRA COMMAND CENTER ", style=f"bold {t.primary}")
    banner_text.append(f"• Theme: {t.label}\n", style=f"dim {t.secondary}")
    banner_text.append(f"  {t.description}", style=f"italic {t.dim}")

    console.print(
        Panel(
            banner_text,
            title=f"[{t.primary}]Preview: {t.name}[/{t.primary}]",
            border_style=t.panel_border,
            padding=(1, 2),
        )
    )

    # 2. Sample UI Table
    table = Table(title=f"[{t.table_header}]System Components Overview[/{t.table_header}]", border_style=t.panel_border)
    table.add_column("Component", style=f"bold {t.primary}")
    table.add_column("Status", style=t.secondary)
    table.add_column("Details", style=t.accent)
    table.add_column("Health", justify="center")

    table.add_row("Rudra Core Engine", f"[{t.success}]Online[/{t.success}]", "v0.1.0 Active", f"[{t.success}]●[/{t.success}]")
    table.add_row("Package Manager", f"[{t.secondary}]Paru / Native[/{t.secondary}]", "325 packages synced", f"[{t.success}]●[/{t.success}]")
    table.add_row("Intrusion Shield", f"[{t.warning}]Monitoring[/{t.warning}]", "Fail2ban active", f"[{t.warning}]▲[/{t.warning}]")
    table.add_row("Security Scan", f"[{t.info}]Lynis Audited[/{t.info}]", "Index score: 82", f"[{t.success}]●[/{t.success}]")

    console.print(table)

    # 3. Palette Swatches
    swatches = [
        ("Primary", t.primary),
        ("Secondary", t.secondary),
        ("Accent", t.accent),
        ("Success", t.success),
        ("Warning", t.warning),
        ("Error", t.error),
    ]
    swatch_line = Text("Palette: ")
    for label, color in swatches:
        swatch_line.append(f" ■ {label} ", style=f"bold {color}")
    console.print(swatch_line)
    console.print()
