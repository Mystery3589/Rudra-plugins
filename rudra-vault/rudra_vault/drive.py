"""Daily Drive Engine for Rudra Secret Safe.

Provides an accessible directory (~/Vault) that decrypts files when unlocked
for daily use, detects edits/additions, and securely wipes when locked.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Optional

from rudra_vault.crypto import ensure_vault_dir, VAULT_DIR
from rudra_vault.storage import (
    add_file,
    add_note,
    delete_item,
    get_item_data,
    list_items,
    store_blob,
    _read_manifest,
    _write_manifest,
)

DEFAULT_DRIVE_DIR = Path.home() / "Vault"
DRIVE_STATE_FILE = VAULT_DIR / ".drive_state.json"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def is_drive_mounted(drive_dir: Optional[Path] = None) -> bool:
    target = drive_dir or DEFAULT_DRIVE_DIR
    return target.exists() and DRIVE_STATE_FILE.exists()


def get_drive_status(drive_dir: Optional[Path] = None) -> dict[str, Any]:
    target = drive_dir or DEFAULT_DRIVE_DIR
    mounted = is_drive_mounted(target)
    item_count = 0
    if mounted and target.is_dir():
        item_count = sum(1 for p in target.iterdir() if not p.name.startswith("."))
    return {
        "mounted": mounted,
        "path": str(target),
        "items_in_drive": item_count,
    }


def mount_drive(key: bytes, drive_dir: Optional[Path] = None) -> dict[str, Any]:
    """Decrypt safe assets into drive_dir for daily use."""
    target = drive_dir or DEFAULT_DRIVE_DIR
    target.mkdir(parents=True, exist_ok=True)
    os.chmod(target, 0o700)

    items = list_items(key=key)
    state: dict[str, Any] = {
        "path": str(target),
        "files": {},  # filename -> {id, sha256, mtime, type}
    }

    count = 0
    for item in items:
        itype = item.get("type")
        name = item.get("name")
        item_id = item.get("id")

        if itype in ("media", "document", "file", "note"):
            try:
                _, data = get_item_data(item_id, key=key)
                file_path = target / name
                file_path.write_bytes(data)
                os.chmod(file_path, 0o600)

                state["files"][name] = {
                    "id": item_id,
                    "sha256": _sha256(data),
                    "mtime": file_path.stat().st_mtime,
                    "type": itype,
                }
                count += 1
            except Exception:
                continue

    ensure_vault_dir()
    DRIVE_STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    os.chmod(DRIVE_STATE_FILE, 0o600)

    return {"status": "mounted", "path": str(target), "count": count}


def sync_drive_to_vault(key: bytes, drive_dir: Optional[Path] = None) -> dict[str, int]:
    """Scan drive_dir for changes, new files, and deletions, syncing back to vault."""
    target = drive_dir or DEFAULT_DRIVE_DIR
    if not target.exists() or not DRIVE_STATE_FILE.exists():
        return {"added": 0, "updated": 0, "deleted": 0}

    try:
        state = json.loads(DRIVE_STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        state = {"path": str(target), "files": {}}

    old_files: dict[str, dict] = state.get("files", {})
    current_files = {p.name: p for p in target.iterdir() if p.is_file() and not p.name.startswith(".")}

    added = 0
    updated = 0
    deleted = 0

    # 1. Check for updated or new files
    for name, path in current_files.items():
        curr_hash = _file_sha256(path)
        if name in old_files:
            # Existing file: check if hash changed
            if curr_hash != old_files[name].get("sha256"):
                item_id = old_files[name].get("id")
                # Update blob in safe
                manifest = _read_manifest(key)
                found = False
                for m in manifest:
                    if m.get("id") == item_id:
                        data = path.read_bytes()
                        blob_id = store_blob(data, key)
                        m["blob_id"] = blob_id
                        m["size_bytes"] = len(data)
                        m["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                        found = True
                        break
                if found:
                    _write_manifest(manifest, key)
                    old_files[name]["sha256"] = curr_hash
                    old_files[name]["mtime"] = path.stat().st_mtime
                    updated += 1
        else:
            # Brand new file dropped into ~/Vault by user
            try:
                # Classify by extension
                if path.suffix.lower() in (".txt", ".md"):
                    content = path.read_text(encoding="utf-8", errors="replace")
                    item = add_note(name, content, tags=["drive"], key=key)
                else:
                    item = add_file(path, alias=name, tags=["drive"], key=key)

                old_files[name] = {
                    "id": item["id"],
                    "sha256": curr_hash,
                    "mtime": path.stat().st_mtime,
                    "type": item.get("type", "document"),
                }
                added += 1
            except Exception:
                continue

    # 2. Check for deleted files
    for name, meta in list(old_files.items()):
        if name not in current_files:
            item_id = meta.get("id")
            if item_id:
                try:
                    delete_item(item_id, key=key)
                    deleted += 1
                except Exception:
                    pass
            del old_files[name]

    state["files"] = old_files
    DRIVE_STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")

    return {"added": added, "updated": updated, "deleted": deleted}


def unmount_drive(key: Optional[bytes] = None, drive_dir: Optional[Path] = None, wipe: bool = True) -> dict[str, Any]:
    """Sync changes and securely wipe the drive directory."""
    target = drive_dir or DEFAULT_DRIVE_DIR
    sync_result = {"added": 0, "updated": 0, "deleted": 0}

    if key and target.exists() and DRIVE_STATE_FILE.exists():
        sync_result = sync_drive_to_vault(key, target)

    if wipe and target.exists():
        # Securely wipe files (truncate then unlink)
        for p in target.glob("**/*"):
            if p.is_file():
                try:
                    sz = p.stat().st_size
                    with open(p, "wb") as f:
                        f.write(os.urandom(min(sz, 4096)))
                    p.unlink(missing_ok=True)
                except Exception:
                    p.unlink(missing_ok=True)
        shutil.rmtree(target, ignore_errors=True)

    DRIVE_STATE_FILE.unlink(missing_ok=True)
    return {"status": "unmounted", "sync": sync_result}


def open_drive_in_file_manager(drive_dir: Optional[Path] = None) -> bool:
    target = drive_dir or DEFAULT_DRIVE_DIR
    if not target.exists():
        return False
    try:
        subprocess.Popen(["xdg-open", str(target)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False
