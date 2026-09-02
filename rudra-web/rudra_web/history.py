"""Execution history manager with auto-expiration for Rudra Web UI."""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

HISTORY_FILE = Path.home() / ".rudra" / "web" / "history.json"
MAX_HISTORY_ENTRIES = 100
MAX_HISTORY_AGE_DAYS = 7


def _ensure_dir():
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_history() -> list[dict]:
    """Load execution history and automatically prune expired records."""
    _ensure_dir()
    if not HISTORY_FILE.exists():
        return []

    try:
        data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            return []
    except Exception:
        return []

    # Auto-prune records older than MAX_HISTORY_AGE_DAYS
    now = time.time()
    cutoff = now - (MAX_HISTORY_AGE_DAYS * 86400)
    pruned = []

    for entry in data:
        ts = entry.get("timestamp_epoch", 0)
        if ts >= cutoff:
            pruned.append(entry)

    # Trim to max entries
    if len(pruned) > MAX_HISTORY_ENTRIES:
        pruned = pruned[:MAX_HISTORY_ENTRIES]

    # Save back if pruned
    if len(pruned) != len(data):
        save_history(pruned)

    return pruned


def save_history(records: list[dict]) -> None:
    _ensure_dir()
    try:
        HISTORY_FILE.write_text(json.dumps(records, indent=2), encoding="utf-8")
    except Exception:
        pass


def record_execution(
    command_str: str,
    args: list[str],
    exit_code: int,
    duration_sec: float,
    output_snippet: str = "",
) -> None:
    """Append a new execution record to the history file with auto-rotation."""
    records = load_history()
    now_epoch = time.time()
    entry = {
        "id": f"run_{int(now_epoch * 1000)}",
        "command": command_str,
        "args": args,
        "exit_code": exit_code,
        "duration_sec": round(duration_sec, 2),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "timestamp_epoch": now_epoch,
        "output_snippet": output_snippet[-2000:] if output_snippet else "",
    }
    # Prepend newest record
    records.insert(0, entry)
    # Enforce max limit
    if len(records) > MAX_HISTORY_ENTRIES:
        records = records[:MAX_HISTORY_ENTRIES]
    save_history(records)


def clear_history() -> None:
    """Wipe all execution history."""
    _ensure_dir()
    try:
        if HISTORY_FILE.exists():
            HISTORY_FILE.write_text("[]", encoding="utf-8")
    except Exception:
        pass
