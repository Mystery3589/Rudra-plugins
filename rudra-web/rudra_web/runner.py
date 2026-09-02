"""Subprocess execution and real-time streaming engine for Rudra Web UI."""

from __future__ import annotations

import asyncio
import os
import shutil
import sys
import time
from typing import AsyncGenerator, Optional

try:
    from rudra.web.history import record_execution
    from rudra.web.sudo import get_cached_sudo_password
except ImportError:
    from rudra_web.history import record_execution
    from rudra_web.sudo import get_cached_sudo_password


async def stream_command(
    command_args: list[str],
    cwd: Optional[str] = None,
) -> AsyncGenerator[dict, None]:
    """Execute command and stream output lines as structured event dicts."""
    t0 = time.time()
    # Resolve rudra executable path
    rudra_bin = shutil.which("rudra") or sys.executable
    if not command_args:
        yield {"type": "error", "data": "Empty command provided"}
        return

    # If first arg is 'rudra', use resolved binary
    if command_args[0] == "rudra":
        full_cmd = [rudra_bin] + command_args[1:]
    else:
        full_cmd = [rudra_bin] + command_args

    cmd_display = " ".join(command_args)
    yield {"type": "start", "command": cmd_display}

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["TERM"] = "xterm-256color"
    env["FORCE_COLOR"] = "1"

    sudo_pw = get_cached_sudo_password()

    try:
        proc = await asyncio.create_subprocess_exec(
            *full_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            stdin=asyncio.subprocess.PIPE if sudo_pw else None,
            cwd=cwd or os.getcwd(),
            env=env,
        )

        output_accumulator = []

        if sudo_pw and proc.stdin:
            try:
                proc.stdin.write(f"{sudo_pw}\n".encode())
                await proc.stdin.drain()
            except Exception:
                pass

        while True:
            if proc.stdout is None:
                break
            line = await proc.stdout.readline()
            if not line:
                break
            decoded = line.decode(errors="replace")
            output_accumulator.append(decoded)
            yield {"type": "stdout", "data": decoded}

        await proc.wait()
        exit_code = proc.returncode or 0
        duration = time.time() - t0
        full_output = "".join(output_accumulator)

        record_execution(
            command_str=cmd_display,
            args=command_args,
            exit_code=exit_code,
            duration_sec=duration,
            output_snippet=full_output,
        )

        yield {
            "type": "exit",
            "exit_code": exit_code,
            "duration": round(duration, 2),
        }

    except Exception as e:
        duration = time.time() - t0
        err_msg = f"Failed to execute command: {e}\n"
        yield {"type": "stdout", "data": err_msg}
        yield {"type": "exit", "exit_code": 1, "duration": round(duration, 2)}
