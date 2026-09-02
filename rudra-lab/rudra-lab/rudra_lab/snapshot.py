"""Snapshot lab state before/after a test run."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table

from rudra_lab.helpers import LAB_DIR, LabConfig, Tier, capture

console = Console()

SNAP_DIR = LAB_DIR / "snapshots"
SNAP_DIR.mkdir(parents=True, exist_ok=True)


def _snap_path(lab_name: str, tag: str) -> Path:
    return SNAP_DIR / f"{lab_name}_{tag}.json"


def _file_hash(p: Path) -> str:
    try:
        h = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
        return h
    except Exception:
        return "?"


def _collect_fs_state(paths: list[str]) -> dict[str, str]:
    """Walk paths and collect {relative_path: sha256[:16]} for all files."""
    state: dict[str, str] = {}
    for root_str in paths:
        root = Path(root_str).expanduser()
        if root.is_file():
            state[str(root)] = _file_hash(root)
        elif root.is_dir():
            for p in sorted(root.rglob("*")):
                if p.is_file():
                    state[str(p)] = _file_hash(p)
    return state


def _collect_docker_state(cfg: LabConfig) -> dict:
    """Collect docker image/container info."""
    code, out = capture(["docker", "inspect", cfg.docker_image])
    return {"image_inspect": out[:2000] if code == 0 else "unavailable"}


def take_snapshot(cfg: LabConfig, tag: str, paths: Optional[list[str]] = None) -> Path:
    """Snapshot the current state of the lab and relevant file paths."""
    ts = datetime.now().isoformat()
    snap: dict = {
        "lab":       cfg.name,
        "tier":      cfg.tier,
        "tag":       tag,
        "timestamp": ts,
        "env_vars":  dict(os.environ),
        "fs":        {},
        "docker":    {},
        "packages":  {},
    }

    # File system state
    watch_paths = paths or cfg.readonly_mounts + cfg.writable_mounts
    if watch_paths:
        snap["fs"] = _collect_fs_state(watch_paths)

    # Docker state
    if Tier(cfg.tier) == Tier.DOCKER:
        snap["docker"] = _collect_docker_state(cfg)

    # Installed packages (best-effort)
    for tool, args in [
        ("pip",  ["pip", "list", "--format=freeze"]),
        ("npm",  ["npm", "list", "-g", "--depth=0"]),
        ("pacman", ["pacman", "-Q"]),
        ("apt",  ["dpkg", "--get-selections"]),
    ]:
        code, out = capture(args, timeout=10)
        if code == 0 and out.strip():
            snap["packages"][tool] = out[:5000]

    out_path = _snap_path(cfg.name, tag)
    out_path.write_text(json.dumps(snap, indent=2, default=str))
    console.print(f"[green]✓ Snapshot '{tag}' saved.[/green]  [dim]{out_path}[/dim]")
    return out_path


def diff_snapshots(cfg: LabConfig, tag_before: str, tag_after: str) -> None:
    """Show what changed between two snapshots."""
    before_path = _snap_path(cfg.name, tag_before)
    after_path  = _snap_path(cfg.name, tag_after)

    if not before_path.exists():
        console.print(f"[red]Snapshot '{tag_before}' not found.[/red]")
        return
    if not after_path.exists():
        console.print(f"[red]Snapshot '{tag_after}' not found.[/red]")
        return

    before = json.loads(before_path.read_text())
    after  = json.loads(after_path.read_text())

    console.print(f"\n[bold]Diff: [cyan]{tag_before}[/cyan] → [cyan]{tag_after}[/cyan][/bold]\n")

    # ── file system diff ─────────────────────────────────────────────────────
    fs_before = before.get("fs", {})
    fs_after  = after.get("fs", {})

    added    = {k: v for k, v in fs_after.items()  if k not in fs_before}
    removed  = {k: v for k, v in fs_before.items() if k not in fs_after}
    modified = {k: v for k, v in fs_after.items()
                if k in fs_before and fs_before[k] != v}

    if added or removed or modified:
        table = Table(title="File System Changes", box=None, show_header=True,
                      header_style="bold dim")
        table.add_column("change", style="bold", no_wrap=True)
        table.add_column("path")
        for p in added:
            table.add_row("[green]added[/green]",   p)
        for p in removed:
            table.add_row("[red]removed[/red]",   p)
        for p in modified:
            table.add_row("[yellow]modified[/yellow]", p)
        console.print(table)
    else:
        console.print("[dim]No file system changes.[/dim]")

    # ── package diff ─────────────────────────────────────────────────────────
    pkg_before = before.get("packages", {})
    pkg_after  = after.get("packages", {})
    pkg_changed = False
    for mgr in set(list(pkg_before.keys()) + list(pkg_after.keys())):
        b_lines = set((pkg_before.get(mgr) or "").splitlines())
        a_lines = set((pkg_after.get(mgr) or "").splitlines())
        new_pkgs = a_lines - b_lines
        gone_pkgs = b_lines - a_lines
        if new_pkgs or gone_pkgs:
            pkg_changed = True
            console.print(f"\n[bold]{mgr} package changes:[/bold]")
            for p in sorted(new_pkgs):
                console.print(f"  [green]+ {p}[/green]")
            for p in sorted(gone_pkgs):
                console.print(f"  [red]- {p}[/red]")
    if not pkg_changed:
        console.print("[dim]No package changes.[/dim]")

    console.print()


def list_snapshots(lab_name: str) -> None:
    snaps = sorted(SNAP_DIR.glob(f"{lab_name}_*.json"))
    if not snaps:
        console.print(f"[dim]No snapshots for lab '{lab_name}'.[/dim]")
        return
    console.print(f"\n[bold]Snapshots for '{lab_name}':[/bold]")
    for s in snaps:
        try:
            data = json.loads(s.read_text())
            console.print(f"  [cyan]{data['tag']:20}[/cyan]  [dim]{data['timestamp']}[/dim]")
        except Exception:
            console.print(f"  [dim]{s.stem}[/dim]")
    console.print()


def delete_snapshot(lab_name: str, tag: str) -> None:
    p = _snap_path(lab_name, tag)
    if p.exists():
        p.unlink()
        console.print(f"[green]✓ Deleted snapshot '{tag}'.[/green]")
    else:
        console.print(f"[yellow]Snapshot '{tag}' not found.[/yellow]")
