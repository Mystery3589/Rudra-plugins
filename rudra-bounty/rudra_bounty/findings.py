"""Local security findings tracker and triage manager.

Maintains an organized, confidential catalog of observed potential
vulnerabilities, endpoints, and remediation notes on the researcher's local machine.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Optional

BOUNTY_DIR = Path.home() / ".rudra" / "bounty"
FINDINGS_FILE = BOUNTY_DIR / "findings.json"

SEVERITY_LEVELS = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
STATUS_LIFECYCLE = ["discovered", "triaged", "reported", "accepted", "resolved", "duplicate", "informative"]


def _load() -> list[dict[str, Any]]:
    if not FINDINGS_FILE.exists():
        return []
    try:
        return json.loads(FINDINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(items: list[dict[str, Any]]) -> None:
    BOUNTY_DIR.mkdir(parents=True, exist_ok=True)
    FINDINGS_FILE.write_text(json.dumps(items, indent=2), encoding="utf-8")
    os.chmod(FINDINGS_FILE, 0o600)


def add_finding(
    title: str,
    target: str,
    severity: str = "MEDIUM",
    category: str = "misconfiguration",
    description: str = "",
    remediation: str = "",
    program: str = "",
) -> dict[str, Any]:
    sev = severity.upper() if severity.upper() in SEVERITY_LEVELS else "MEDIUM"
    item = {
        "id": str(uuid.uuid4())[:8],
        "title": title,
        "target": target,
        "program": program or "default",
        "severity": sev,
        "category": category,
        "description": description,
        "remediation": remediation,
        "status": "discovered",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    items = _load()
    items.insert(0, item)
    _save(items)
    return item


def list_findings(
    program: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
) -> list[dict[str, Any]]:
    items = _load()
    if program:
        items = [i for i in items if i.get("program") == program]
    if severity:
        items = [i for i in items if i.get("severity") == severity.upper()]
    if status:
        items = [i for i in items if i.get("status") == status.lower()]
    return items


def get_finding(finding_id: str) -> Optional[dict[str, Any]]:
    items = _load()
    for item in items:
        if item.get("id") == finding_id:
            return item
    return None


def update_finding_status(finding_id: str, new_status: str, note: str = "") -> bool:
    items = _load()
    for item in items:
        if item.get("id") == finding_id:
            item["status"] = new_status.lower()
            item["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            if note:
                item.setdefault("notes", []).append({
                    "timestamp": item["updated_at"],
                    "note": note,
                })
            _save(items)
            return True
    return False


def delete_finding(finding_id: str) -> bool:
    items = _load()
    new_items = [i for i in items if i.get("id") != finding_id]
    if len(new_items) != len(items):
        _save(new_items)
        return True
    return False
