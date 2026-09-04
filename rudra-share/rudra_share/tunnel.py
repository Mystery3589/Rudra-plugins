"""Tunnel process orchestrator for rudra-share.

Handles starting, tracking, and stopping public reverse tunnels.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import signal
import subprocess
import time
from pathlib import Path
from typing import Any, Optional

SHARE_DIR = Path.home() / ".rudra" / "share"
STATE_FILE = SHARE_DIR / "tunnels.json"
LOG_DIR = SHARE_DIR / "logs"

URL_REGEX = re.compile(r"https://[a-zA-Z0-9.-]+\.(lhr\.life|pinggy\.link|trycloudflare\.com|localhost\.run)")


def _load_state() -> dict[str, dict[str, Any]]:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(data: dict[str, dict[str, Any]]) -> None:
    SHARE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _is_pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def list_tunnels() -> list[dict[str, Any]]:
    """List all active tunnels and clean up dead processes."""
    state = _load_state()
    active = []
    changed = False

    for port_str, info in list(state.items()):
        pid = info.get("pid")
        if pid and _is_pid_alive(pid):
            active.append(info)
        else:
            del state[port_str]
            changed = True

    if changed:
        _save_state(state)
    return active


def start_tunnel(port: int, backend: str = "auto") -> dict[str, Any]:
    """Start a public tunnel for localhost:port in background."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"tunnel_{port}.log"

    # Determine command based on backend availability
    if backend == "cloudflare" or (backend == "auto" and shutil.which("cloudflared")):
        if shutil.which("cloudflared"):
            cmd = ["cloudflared", "tunnel", "--url", f"http://localhost:{port}"]
            used_backend = "cloudflared"
        else:
            cmd = [
                "ssh", "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
                "-o", "ServerAliveInterval=30", "-R", f"80:localhost:{port}", "nokey@localhost.run"
            ]
            used_backend = "localhost.run"
    else:
        cmd = [
            "ssh", "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
            "-o", "ServerAliveInterval=30", "-R", f"80:localhost:{port}", "nokey@localhost.run"
        ]
        used_backend = "localhost.run"

    # Launch background process
    with open(log_file, "w") as out:
        proc = subprocess.Popen(
            cmd,
            stdout=out,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )

    # Wait for public URL in logs
    public_url = None
    start_time = time.time()
    while time.time() - start_time < 12:
        if not _is_pid_alive(proc.pid):
            break
        if log_file.exists():
            content = log_file.read_text(encoding="utf-8", errors="replace")
            # Check regex
            m = URL_REGEX.search(content)
            if m:
                public_url = m.group(0)
                break
            # Generic fallback check for https://
            for line in content.splitlines():
                if "https://" in line and ("lhr.life" in line or "pinggy" in line or "trycloudflare" in line):
                    for word in line.split():
                        if word.startswith("https://"):
                            public_url = word.strip().rstrip(".,")
                            break
            if public_url:
                break
        time.sleep(0.5)

    if not public_url and _is_pid_alive(proc.pid):
        # Even if not found immediately, give the generic placeholder or fallback
        content = log_file.read_text(encoding="utf-8", errors="replace") if log_file.exists() else ""
        urls = re.findall(r"https://[^\s'\"<]+", content)
        if urls:
            public_url = urls[-1].rstrip(".,")

    if not public_url:
        try:
            os.kill(proc.pid, signal.SIGTERM)
        except Exception:
            pass
        return {
            "success": False,
            "error": "Failed to establish tunnel or obtain public URL. Check internet connection.",
        }

    tunnel_info = {
        "port": port,
        "pid": proc.pid,
        "url": public_url,
        "backend": used_backend,
        "log_path": str(log_file),
        "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    state = _load_state()
    state[str(port)] = tunnel_info
    _save_state(state)

    return {"success": True, "tunnel": tunnel_info}


def stop_tunnel(target: int | str) -> list[int]:
    """Stop one or all active tunnels."""
    state = _load_state()
    stopped = []

    if str(target).lower() == "all":
        ports_to_stop = list(state.keys())
    else:
        ports_to_stop = [str(target)] if str(target) in state else []

    for p in ports_to_stop:
        info = state.get(p)
        if info:
            pid = info.get("pid")
            if pid and _is_pid_alive(pid):
                try:
                    os.kill(pid, signal.SIGTERM)
                    time.sleep(0.2)
                    if _is_pid_alive(pid):
                        os.kill(pid, signal.SIGKILL)
                except Exception:
                    pass
            stopped.append(int(p))
            del state[p]

    _save_state(state)
    return stopped
