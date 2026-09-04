"""Known configuration targets and path resolution."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

DOTFILES_DIR = Path.home() / ".rudra" / "dotfiles"
TARGETS_FILE = DOTFILES_DIR / "targets.json"

DEFAULT_TARGETS: dict[str, dict] = {
    "zsh": {
        "label": "Zsh Shell Config",
        "path": "~/.zshrc",
        "is_dir": False,
    },
    "bash": {
        "label": "Bash Shell Config",
        "path": "~/.bashrc",
        "is_dir": False,
    },
    "nvim": {
        "label": "Neovim Config Directory",
        "path": "~/.config/nvim",
        "is_dir": True,
    },
    "tmux": {
        "label": "Tmux Multiplexer Config",
        "path": "~/.tmux.conf",
        "is_dir": False,
    },
    "kitty": {
        "label": "Kitty Terminal Config",
        "path": "~/.config/kitty",
        "is_dir": True,
    },
    "alacritty": {
        "label": "Alacritty Terminal Config",
        "path": "~/.config/alacritty",
        "is_dir": True,
    },
    "git": {
        "label": "Global Git Config",
        "path": "~/.gitconfig",
        "is_dir": False,
    },
    "starship": {
        "label": "Starship Prompt Config",
        "path": "~/.config/starship.toml",
        "is_dir": False,
    },
    "fish": {
        "label": "Fish Shell Config",
        "path": "~/.config/fish",
        "is_dir": True,
    },
    "hyprland": {
        "label": "Hyprland Compositor Config",
        "path": "~/.config/hypr",
        "is_dir": True,
    },
    "fastfetch": {
        "label": "Fastfetch System Info Config",
        "path": "~/.config/fastfetch",
        "is_dir": True,
    },
}


def _load_custom_targets() -> dict[str, dict]:
    if not TARGETS_FILE.exists():
        return {}
    try:
        return json.loads(TARGETS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_custom_targets(data: dict[str, dict]) -> None:
    DOTFILES_DIR.mkdir(parents=True, exist_ok=True)
    TARGETS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_all_targets() -> dict[str, dict]:
    """Returns combined built-in and user-custom targets."""
    targets = dict(DEFAULT_TARGETS)
    targets.update(_load_custom_targets())
    return targets


def resolve_target(name: str) -> Optional[dict]:
    """Lookup a target definition by name (case-insensitive)."""
    all_t = get_all_targets()
    name_clean = name.lower().strip()
    if name_clean in all_t:
        info = dict(all_t[name_clean])
        info["resolved_path"] = Path(info["path"]).expanduser().resolve()
        info["name"] = name_clean
        return info
    return None


def register_custom_target(name: str, path_str: str, label: str = "") -> dict:
    """Register a custom path as a tracked dotfile target."""
    p = Path(path_str).expanduser().resolve()
    is_dir = p.is_dir() or (not p.exists() and not p.suffix)
    entry = {
        "label": label or f"Custom {name}",
        "path": str(p),
        "is_dir": is_dir,
    }
    custom = _load_custom_targets()
    custom[name.lower().strip()] = entry
    _save_custom_targets(custom)
    return entry
