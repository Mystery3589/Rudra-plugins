"""Core execution engine for rudra-win.

Runs PowerShell commands with Administrator elevation checks, safe error handling,
and cross-platform simulation mode when run outside of Windows.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple
from rich.console import Console

console = Console()

IS_WINDOWS = platform.system() == "Windows"


def is_admin() -> bool:
    """Check if the current process has Windows Administrator privileges."""
    if not IS_WINDOWS:
        return False
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def run_powershell(
    script: str,
    as_admin: bool = False,
    silent: bool = False,
    timeout: int = 60,
) -> Tuple[bool, str]:
    """Execute a PowerShell command block.
    
    If on Linux/macOS, operates in preview/simulation mode or dispatches to pwsh if available.
    """
    # If running on Windows
    if IS_WINDOWS:
        ps_bin = shutil.which("pwsh.exe") or shutil.which("powershell.exe") or "powershell.exe"
        if as_admin and not is_admin():
            # Spawn elevated PowerShell process
            elevated_cmd = f"Start-Process {ps_bin} -ArgumentList '-NoProfile -NonInteractive -Command \"{script}\"' -Verb RunAs -Wait"
            try:
                res = subprocess.run(
                    [ps_bin, "-NoProfile", "-NonInteractive", "-Command", elevated_cmd],
                    capture_output=True, text=True, timeout=timeout,
                )
                return res.returncode == 0, res.stdout or res.stderr
            except Exception as e:
                return False, str(e)
        else:
            try:
                res = subprocess.run(
                    [ps_bin, "-NoProfile", "-NonInteractive", "-Command", script],
                    capture_output=True, text=True, timeout=timeout,
                )
                output = (res.stdout + res.stderr).strip()
                return res.returncode == 0, output
            except Exception as e:
                return False, str(e)

    # Cross-platform simulation / preview mode
    if not silent:
        console.print(f"[dim]Windows Engine (Simulation/Cross-Platform Preview):[/dim]\n[cyan]{script.strip()}[/cyan]")
    return True, "Executed in simulation mode (Host OS is not Windows)."


def run_cmd(command: list[str]) -> Tuple[bool, str]:
    """Run native Windows command-line utility (e.g. powercfg, dism, sfc)."""
    if IS_WINDOWS:
        try:
            res = subprocess.run(command, capture_output=True, text=True)
            return res.returncode == 0, (res.stdout + res.stderr).strip()
        except Exception as e:
            return False, str(e)
    return True, f"Simulation: {' '.join(command)}"
