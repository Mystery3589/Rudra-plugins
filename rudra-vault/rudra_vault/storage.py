"""Encrypted storage manager for Rudra Secret Safe."""

from __future__ import annotations

import json
import mimetypes
import os
import shutil
import time
import uuid
from pathlib import Path
from typing import Any, Optional

from rudra_vault.crypto import (
    VAULT_DIR,
    decrypt_bytes,
    encrypt_bytes,
    ensure_vault_dir,
    get_cached_session_key,
    is_initialized,
    is_unlocked,
    clear_session_key,
)

MANIFEST_FILE = VAULT_DIR / "vault_manifest.enc"
BLOBS_DIR = VAULT_DIR / "blobs"


def _read_manifest(key: bytes) -> list[dict[str, Any]]:
    if not MANIFEST_FILE.exists():
        return []
    try:
        raw = MANIFEST_FILE.read_bytes()
        decrypted = decrypt_bytes(raw, key)
        return json.loads(decrypted.decode("utf-8"))
    except Exception as e:
        raise ValueError(f"Could not decrypt vault manifest: {e}")


def _write_manifest(items: list[dict[str, Any]], key: bytes) -> None:
    ensure_vault_dir()
    raw = json.dumps(items, indent=2).encode("utf-8")
    encrypted = encrypt_bytes(raw, key)
    MANIFEST_FILE.write_bytes(encrypted)
    os.chmod(MANIFEST_FILE, 0o600)


def classify_type(mime_type: str, filename: str) -> str:
    """Classify item type based on mime type and extension."""
    if mime_type.startswith("image/") or mime_type.startswith("video/") or mime_type.startswith("audio/"):
        return "media"
    ext = Path(filename).suffix.lower()
    if ext in (".pdf", ".docx", ".doc", ".txt", ".md", ".csv", ".json", ".yaml", ".yml", ".xml", ".rtf", ".odt"):
        return "document"
    if mime_type.startswith("text/"):
        return "document"
    return "document"


def store_blob(data: bytes, key: bytes) -> str:
    """Encrypt and store arbitrary bytes into blobs/<blob_id>.enc. Returns blob_id."""
    ensure_vault_dir()
    blob_id = str(uuid.uuid4())
    blob_file = BLOBS_DIR / f"{blob_id}.enc"
    encrypted = encrypt_bytes(data, key)
    blob_file.write_bytes(encrypted)
    os.chmod(blob_file, 0o600)
    return blob_id


def read_blob(blob_id: str, key: bytes) -> bytes:
    """Read and decrypt blob payload."""
    blob_file = BLOBS_DIR / f"{blob_id}.enc"
    if not blob_file.exists():
        raise FileNotFoundError(f"Encrypted blob '{blob_id}' not found")
    encrypted = blob_file.read_bytes()
    return decrypt_bytes(encrypted, key)


def delete_blob(blob_id: str) -> None:
    blob_file = BLOBS_DIR / f"{blob_id}.enc"
    if blob_file.exists():
        try:
            blob_file.unlink(missing_ok=True)
        except Exception:
            pass


# ── High Level Safe APIs ───────────────────────────────────────────────────

def add_secret(name: str, value: str, category: str = "api_key", tags: list[str] = None, key: Optional[bytes] = None) -> dict[str, Any]:
    active_key = key or get_cached_session_key()
    if not active_key:
        raise PermissionError("Vault is locked")

    items = _read_manifest(active_key)
    # Remove existing with same name if any
    for old in [i for i in items if i["name"] == name and i["type"] == "secret"]:
        delete_blob(old.get("blob_id", ""))
    items = [i for i in items if not (i["name"] == name and i["type"] == "secret")]

    blob_id = store_blob(value.encode("utf-8"), active_key)
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
    item = {
        "id": str(uuid.uuid4()),
        "name": name,
        "type": "secret",
        "category": category,
        "mime_type": "text/plain",
        "size_bytes": len(value.encode("utf-8")),
        "tags": tags or [category],
        "blob_id": blob_id,
        "created_at": now_str,
        "updated_at": now_str,
        "preview": "••••••••••••",
    }
    items.append(item)
    _write_manifest(items, active_key)
    return item


def add_note(title: str, content: str, tags: list[str] = None, key: Optional[bytes] = None) -> dict[str, Any]:
    active_key = key or get_cached_session_key()
    if not active_key:
        raise PermissionError("Vault is locked")

    items = _read_manifest(active_key)
    for old in [i for i in items if i["name"] == title and i["type"] == "note"]:
        delete_blob(old.get("blob_id", ""))
    items = [i for i in items if not (i["name"] == title and i["type"] == "note")]

    blob_id = store_blob(content.encode("utf-8"), active_key)
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
    snippet = content.replace("\n", " ")[:120]
    item = {
        "id": str(uuid.uuid4()),
        "name": title,
        "type": "note",
        "category": "note",
        "mime_type": "text/markdown",
        "size_bytes": len(content.encode("utf-8")),
        "tags": tags or ["note"],
        "blob_id": blob_id,
        "created_at": now_str,
        "updated_at": now_str,
        "preview": snippet + ("..." if len(content) > 120 else ""),
    }
    items.append(item)
    _write_manifest(items, active_key)
    return item


def add_file(filepath: Path, alias: Optional[str] = None, tags: list[str] = None, key: Optional[bytes] = None) -> dict[str, Any]:
    active_key = key or get_cached_session_key()
    if not active_key:
        raise PermissionError("Vault is locked")
    if not filepath.exists():
        raise FileNotFoundError(f"File '{filepath}' not found")

    data = filepath.read_bytes()
    name = alias or filepath.name
    mime_type, _ = mimetypes.guess_type(str(filepath))
    mime_type = mime_type or "application/octet-stream"
    item_type = classify_type(mime_type, filepath.name)

    items = _read_manifest(active_key)
    for old in [i for i in items if i["name"] == name]:
        delete_blob(old.get("blob_id", ""))
    items = [i for i in items if i["name"] != name]

    blob_id = store_blob(data, active_key)
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
    item = {
        "id": str(uuid.uuid4()),
        "name": name,
        "type": item_type,
        "category": item_type,
        "mime_type": mime_type,
        "size_bytes": len(data),
        "tags": tags or [item_type],
        "blob_id": blob_id,
        "created_at": now_str,
        "updated_at": now_str,
        "preview": f"{round(len(data) / 1024, 1)} KB",
    }
    items.append(item)
    _write_manifest(items, active_key)
    return item


def add_file_bytes(data: bytes, filename: str, mime_type: Optional[str] = None, tags: list[str] = None, key: Optional[bytes] = None) -> dict[str, Any]:
    active_key = key or get_cached_session_key()
    if not active_key:
        raise PermissionError("Vault is locked")

    if not mime_type:
        mime_type, _ = mimetypes.guess_type(filename)
        mime_type = mime_type or "application/octet-stream"
    item_type = classify_type(mime_type, filename)

    items = _read_manifest(active_key)
    for old in [i for i in items if i["name"] == filename]:
        delete_blob(old.get("blob_id", ""))
    items = [i for i in items if i["name"] != filename]

    blob_id = store_blob(data, active_key)
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
    item = {
        "id": str(uuid.uuid4()),
        "name": filename,
        "type": item_type,
        "category": item_type,
        "mime_type": mime_type,
        "size_bytes": len(data),
        "tags": tags or [item_type],
        "blob_id": blob_id,
        "created_at": now_str,
        "updated_at": now_str,
        "preview": f"{round(len(data) / 1024, 1)} KB",
    }
    items.append(item)
    _write_manifest(items, active_key)
    return item


def list_items(filter_type: Optional[str] = None, key: Optional[bytes] = None) -> list[dict[str, Any]]:
    active_key = key or get_cached_session_key()
    if not active_key:
        raise PermissionError("Vault is locked")

    items = _read_manifest(active_key)
    if filter_type:
        items = [i for i in items if i.get("type") == filter_type]
    return sorted(items, key=lambda x: x.get("created_at", ""), reverse=True)


def get_item(item_id_or_name: str, key: Optional[bytes] = None) -> Optional[dict[str, Any]]:
    active_key = key or get_cached_session_key()
    if not active_key:
        raise PermissionError("Vault is locked")

    items = _read_manifest(active_key)
    for item in items:
        if item["id"] == item_id_or_name or item["name"] == item_id_or_name:
            return item
    return None


def get_item_data(item_id_or_name: str, key: Optional[bytes] = None) -> tuple[dict[str, Any], bytes]:
    active_key = key or get_cached_session_key()
    if not active_key:
        raise PermissionError("Vault is locked")

    item = get_item(item_id_or_name, active_key)
    if not item:
        raise FileNotFoundError(f"Vault item '{item_id_or_name}' not found")

    data = read_blob(item["blob_id"], active_key)
    return item, data


def delete_item(item_id_or_name: str, key: Optional[bytes] = None) -> bool:
    active_key = key or get_cached_session_key()
    if not active_key:
        raise PermissionError("Vault is locked")

    items = _read_manifest(active_key)
    target = None
    for item in items:
        if item["id"] == item_id_or_name or item["name"] == item_id_or_name:
            target = item
            break

    if not target:
        return False

    delete_blob(target.get("blob_id", ""))
    items = [i for i in items if i["id"] != target["id"]]
    _write_manifest(items, active_key)
    return True


def get_vault_stats() -> dict[str, Any]:
    """Return summary stats without requiring unlock."""
    init = is_initialized()
    unlocked = is_unlocked()
    blobs_count = 0
    blobs_size_bytes = 0

    if BLOBS_DIR.exists():
        for f in BLOBS_DIR.glob("*.enc"):
            blobs_count += 1
            blobs_size_bytes += f.stat().st_size

    size_mb = round(blobs_size_bytes / (1024 * 1024), 2)
    return {
        "initialized": init,
        "unlocked": unlocked,
        "total_items": blobs_count,
        "storage_mb": size_mb,
        "storage_bytes": blobs_size_bytes,
    }
