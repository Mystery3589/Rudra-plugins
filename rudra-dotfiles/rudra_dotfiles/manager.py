"""Multi-profile storage, switching, and auto-backup engine."""

from __future__ import annotations

import difflib
import json
import os
import shutil
import time
from pathlib import Path
from typing import Any, Optional

from rudra_dotfiles.targets import DOTFILES_DIR, resolve_target, get_all_targets

STORE_DIR = DOTFILES_DIR / "store"
HISTORY_DIR = DOTFILES_DIR / "history"
STATE_FILE = DOTFILES_DIR / "state.json"


def _load_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {"active": {}}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"active": {}}


def _save_state(data: dict[str, Any]) -> None:
    DOTFILES_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _copy_item(src: Path, dst: Path) -> None:
    """Safely copy either a file or directory."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.is_symlink() or dst.exists():
        if dst.is_dir() and not dst.is_symlink():
            shutil.rmtree(dst)
        else:
            dst.unlink(missing_ok=True)

    if src.is_dir():
        shutil.copytree(src, dst, symlinks=True)
    else:
        shutil.copy2(src, dst)


def _get_target_live_path(target_name: str) -> Optional[tuple[dict, Path]]:
    info = resolve_target(target_name)
    if not info:
        return None
    return info, info["resolved_path"]


# ── Live Capture & Auto-Backup ───────────────────────────────────────────────

def auto_backup_live(target_name: str) -> Optional[str]:
    """Safety mechanism: captures current live file before any destructive switch."""
    res = _get_target_live_path(target_name)
    if not res:
        return None
    _, live_path = res
    if not live_path.exists():
        return None

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    target_hist_dir = HISTORY_DIR / target_name / timestamp
    target_hist_dir.mkdir(parents=True, exist_ok=True)

    dest = target_hist_dir / live_path.name
    _copy_item(live_path, dest)
    return timestamp


def save_current_config(target_name: str, profile_name: str = "current") -> dict[str, Any]:
    """Capture live config from the system into a named profile."""
    res = _get_target_live_path(target_name)
    if not res:
        return {"success": False, "error": f"Unknown dotfile target: '{target_name}'"}
    info, live_path = res

    if not live_path.exists():
        return {"success": False, "error": f"Live file/dir does not exist at {live_path}"}

    profile_dir = STORE_DIR / target_name / profile_name
    dest = profile_dir / live_path.name
    _copy_item(live_path, dest)

    state = _load_state()
    state.setdefault("active", {})[target_name] = profile_name
    _save_state(state)

    return {
        "success": True,
        "target": target_name,
        "profile": profile_name,
        "source": str(live_path),
        "stored_at": str(dest),
    }


# ── Profile Switching ───────────────────────────────────────────────────────

def switch_profile(target_name: str, profile_name: str) -> dict[str, Any]:
    """Switch active profile with automatic safety backup of current live config."""
    res = _get_target_live_path(target_name)
    if not res:
        return {"success": False, "error": f"Unknown dotfile target: '{target_name}'"}
    info, live_path = res

    profile_dir = STORE_DIR / target_name / profile_name
    stored_item = profile_dir / live_path.name
    if not stored_item.exists():
        # Maybe the profile stored it directly under profile_dir
        if (profile_dir).exists() and not info["is_dir"]:
            files = list(profile_dir.iterdir())
            if files:
                stored_item = files[0]
            else:
                return {"success": False, "error": f"Profile '{profile_name}' for '{target_name}' is empty."}
        else:
            return {"success": False, "error": f"Profile '{profile_name}' for '{target_name}' not found."}

    # Step 1: Automatic live safety backup!
    backup_id = auto_backup_live(target_name)

    # Step 2: Replace live config with stored profile
    _copy_item(stored_item, live_path)

    # Step 3: Update state
    state = _load_state()
    state.setdefault("active", {})[target_name] = profile_name
    _save_state(state)

    return {
        "success": True,
        "target": target_name,
        "profile": profile_name,
        "backup_id": backup_id,
        "live_path": str(live_path),
    }


def create_profile(target_name: str, profile_name: str, content: str = "") -> dict[str, Any]:
    """Create a new profile for a target."""
    res = _get_target_live_path(target_name)
    if not res:
        return {"success": False, "error": f"Unknown target: '{target_name}'"}
    info, live_path = res

    profile_dir = STORE_DIR / target_name / profile_name
    profile_dir.mkdir(parents=True, exist_ok=True)
    target_file = profile_dir / live_path.name

    if info["is_dir"]:
        target_file.mkdir(parents=True, exist_ok=True)
    else:
        if content:
            target_file.write_text(content, encoding="utf-8")
        elif live_path.exists():
            _copy_item(live_path, target_file)
        else:
            target_file.write_text(f"# {target_name} config - {profile_name}\n", encoding="utf-8")

    return {"success": True, "target": target_name, "profile": profile_name, "path": str(target_file)}


# ── Listing & Querying ───────────────────────────────────────────────────────

def list_profiles(target_name: Optional[str] = None) -> list[dict[str, Any]]:
    """List all stored profiles and active state."""
    state = _load_state()
    active_map = state.get("active", {})
    all_targets = get_all_targets()

    targets_to_inspect = [target_name] if target_name else list(all_targets.keys())
    results = []

    for t_name in targets_to_inspect:
        t_dir = STORE_DIR / t_name
        active_prof = active_map.get(t_name)
        profiles = []
        if t_dir.exists():
            for p_folder in sorted(t_dir.iterdir()):
                if p_folder.is_dir():
                    profiles.append(p_folder.name)

        t_info = all_targets.get(t_name, {})
        results.append({
            "target": t_name,
            "label": t_info.get("label", t_name),
            "system_path": t_info.get("path", "—"),
            "active_profile": active_prof,
            "profiles": profiles,
            "count": len(profiles),
        })
    return results


def diff_profiles(target_name: str, p1: str, p2: Optional[str] = None) -> str:
    """Generate unified diff between two profiles or profile vs live config."""
    res = _get_target_live_path(target_name)
    if not res:
        return f"Unknown target: {target_name}"
    info, live_path = res

    if info["is_dir"]:
        return "Diffing directories is not supported directly. Please inspect files individually."

    file1 = STORE_DIR / target_name / p1 / live_path.name
    if not file1.exists():
        return f"Profile '{p1}' not found."

    if p2:
        file2 = STORE_DIR / target_name / p2 / live_path.name
        label2 = f"profile:{p2}"
    else:
        file2 = live_path
        label2 = f"live:{live_path}"

    if not file2.exists():
        return f"Target '{label2}' does not exist."

    lines1 = file1.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    lines2 = file2.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)

    diff = difflib.unified_diff(
        lines1, lines2,
        fromfile=f"profile:{p1}",
        tofile=label2,
        lineterm=""
    )
    return "".join(diff)


def list_history(target_name: str) -> list[dict[str, Any]]:
    """List historical auto-backups for a target."""
    t_hist = HISTORY_DIR / target_name
    if not t_hist.exists():
        return []
    items = []
    for snap in sorted(t_hist.iterdir(), reverse=True):
        if snap.is_dir():
            items.append({
                "timestamp": snap.name,
                "path": str(snap),
            })
    return items


def restore_backup(target_name: str, timestamp: str) -> bool:
    """Restore a historical snapshot back to live config."""
    res = _get_target_live_path(target_name)
    if not res:
        return False
    info, live_path = res

    backup_folder = HISTORY_DIR / target_name / timestamp
    if not backup_folder.exists():
        return False

    files = list(backup_folder.iterdir())
    if not files:
        return False

    _copy_item(files[0], live_path)
    return True
