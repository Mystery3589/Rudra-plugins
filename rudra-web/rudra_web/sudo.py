"""Sudo & Privilege Elevation manager for Rudra Web UI."""

from __future__ import annotations

import asyncio
import subprocess
from typing import Optional

_CACHED_SUDO_PASSWORD: Optional[str] = None
_KEEPALIVE_TASK: Optional[asyncio.Task] = None


def has_nopasswd_sudo() -> bool:
    """Test if current user has passwordless sudo configured."""
    try:
        res = subprocess.run(["sudo", "-n", "true"], capture_output=True)
        return res.returncode == 0
    except Exception:
        return False


def set_cached_sudo_password(password: str) -> bool:
    """Validate password against sudo and hold in RAM memory if correct."""
    global _CACHED_SUDO_PASSWORD
    try:
        proc = subprocess.Popen(
            ["sudo", "-S", "-v"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        _, err = proc.communicate(input=f"{password}\n", timeout=5)
        if proc.returncode == 0:
            _CACHED_SUDO_PASSWORD = password
            _start_keepalive()
            return True
        return False
    except Exception:
        return False


def get_cached_sudo_password() -> Optional[str]:
    return _CACHED_SUDO_PASSWORD


def clear_cached_sudo_password() -> None:
    global _CACHED_SUDO_PASSWORD, _KEEPALIVE_TASK
    _CACHED_SUDO_PASSWORD = None
    if _KEEPALIVE_TASK and not _KEEPALIVE_TASK.done():
        _KEEPALIVE_TASK.cancel()


def _start_keepalive():
    """Start background refresh loop for sudo credential timestamp."""
    global _KEEPALIVE_TASK
    if _KEEPALIVE_TASK and not _KEEPALIVE_TASK.done():
        return

    async def loop():
        while True:
            await asyncio.sleep(300)  # refresh every 5 minutes
            pw = get_cached_sudo_password()
            if pw:
                try:
                    proc = await asyncio.create_subprocess_exec(
                        "sudo", "-S", "-v",
                        stdin=asyncio.subprocess.PIPE,
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL,
                    )
                    await proc.communicate(input=f"{pw}\n".encode())
                except Exception:
                    pass
            else:
                break

    try:
        loop_obj = asyncio.get_event_loop()
        _KEEPALIVE_TASK = loop_obj.create_task(loop())
    except Exception:
        pass
