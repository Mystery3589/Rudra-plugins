"""Scope & Rules of Engagement manager.

Enforces in-scope / out-of-scope boundaries so every command validates
targets before sending a single packet — a first-class requirement for
responsible bug bounty work.
"""
from __future__ import annotations

import fnmatch
import json
import os
from pathlib import Path
from typing import Optional

BOUNTY_DIR = Path.home() / ".rudra" / "bounty"
SCOPE_FILE  = BOUNTY_DIR / "scopes.json"


def _load() -> dict:
    if not SCOPE_FILE.exists():
        return {}
    try:
        return json.loads(SCOPE_FILE.read_text())
    except Exception:
        return {}


def _save(data: dict) -> None:
    BOUNTY_DIR.mkdir(parents=True, exist_ok=True)
    SCOPE_FILE.write_text(json.dumps(data, indent=2))
    os.chmod(SCOPE_FILE, 0o600)


# ── Public API ────────────────────────────────────────────────────────────────

def list_programs() -> list[dict]:
    d = _load()
    return [{"name": k, **v} for k, v in d.items()]


def get_program(name: str) -> Optional[dict]:
    return _load().get(name)


def get_active_program() -> Optional[tuple[str, dict]]:
    d = _load()
    for name, prog in d.items():
        if prog.get("active"):
            return name, prog
    return None


def add_program(
    name: str,
    platform: str,
    in_scope: list[str],
    out_of_scope: list[str],
    notes: str = "",
) -> None:
    d = _load()
    d[name] = {
        "platform": platform,
        "in_scope": in_scope,
        "out_of_scope": out_of_scope,
        "notes": notes,
        "active": False,
    }
    _save(d)


def set_active(name: str) -> bool:
    d = _load()
    if name not in d:
        return False
    for k in d:
        d[k]["active"] = (k == name)
    _save(d)
    return True


def remove_program(name: str) -> bool:
    d = _load()
    if name not in d:
        return False
    del d[name]
    _save(d)
    return True


def check_target(target: str, program_name: Optional[str] = None) -> dict:
    """
    Returns {"allowed": bool, "reason": str, "program": str|None, "matched_rule": str|None}
    Uses the active program if program_name is None.
    """
    d = _load()
    if program_name:
        prog = d.get(program_name)
        pname = program_name
    else:
        active = get_active_program()
        if not active:
            return {"allowed": True, "reason": "No active program — proceeding without scope guard.", "program": None, "matched_rule": None}
        pname, prog = active

    if not prog:
        return {"allowed": False, "reason": f"Program '{pname}' not found.", "program": pname, "matched_rule": None}

    host = target.replace("https://", "").replace("http://", "").split("/")[0]

    # Check out-of-scope first
    for rule in prog.get("out_of_scope", []):
        if fnmatch.fnmatch(host, rule) or host == rule:
            return {
                "allowed": False,
                "reason": f"OUT OF SCOPE: '{host}' matches exclusion rule '{rule}' in program '{pname}'.",
                "program": pname,
                "matched_rule": rule,
            }

    # Check in-scope
    for rule in prog.get("in_scope", []):
        if fnmatch.fnmatch(host, rule) or host == rule:
            return {
                "allowed": True,
                "reason": f"IN SCOPE: '{host}' matches rule '{rule}' in program '{pname}'.",
                "program": pname,
                "matched_rule": rule,
            }

    return {
        "allowed": False,
        "reason": f"NOT IN SCOPE: '{host}' does not match any in-scope rule for program '{pname}'.",
        "program": pname,
        "matched_rule": None,
    }
