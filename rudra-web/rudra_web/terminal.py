"""Interactive PTY WebSocket session handler for Rudra Web Terminal."""

from __future__ import annotations

import asyncio
import fcntl
import json
import os
import pty
import select
import signal
import struct
import termios
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect


async def handle_terminal_websocket(websocket: WebSocket) -> None:
    """Handle interactive full-shell PTY WebSocket connection."""
    await websocket.accept()

    # Determine default shell
    shell = os.environ.get("SHELL") or "/bin/bash"
    if not os.path.exists(shell):
        shell = "/bin/sh"

    # Fork PTY
    master_fd, slave_fd = pty.openpty()

    # Set non-blocking on master_fd
    fl = fcntl.fcntl(master_fd, fcntl.F_GETFL)
    fcntl.fcntl(master_fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

    # Set initial window size (default 80x24)
    try:
        winsize = struct.pack("HHHH", 24, 80, 0, 0)
        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)
    except Exception:
        pass

    env = os.environ.copy()
    env["TERM"] = "xterm-256color"
    env["COLORTERM"] = "truecolor"

    pid = os.fork()
    if pid == 0:
        # Child process: configure terminal and launch shell
        try:
            os.close(master_fd)
            os.setsid()
            fcntl.ioctl(slave_fd, termios.TIOCSCTTY, 0)
            os.dup2(slave_fd, 0)
            os.dup2(slave_fd, 1)
            os.dup2(slave_fd, 2)
            if slave_fd > 2:
                os.close(slave_fd)
            os.execvpe(shell, [shell, "-l"], env)
        except Exception:
            os._exit(1)

    # Parent process
    os.close(slave_fd)

    async def pty_to_ws():
        """Read output from shell PTY and send to browser WebSocket."""
        loop = asyncio.get_running_loop()
        try:
            while True:
                # Wait until master_fd is readable
                await loop.run_in_executor(None, select.select, [master_fd], [], [], 0.05)
                try:
                    data = os.read(master_fd, 4096)
                    if not data:
                        break
                    # Send decoded or binary data
                    await websocket.send_text(data.decode("utf-8", errors="replace"))
                except (BlockingIOError, InterruptedError):
                    await asyncio.sleep(0.01)
                except OSError:
                    break
        except (WebSocketDisconnect, asyncio.CancelledError):
            pass
        except Exception:
            pass

    async def ws_to_pty():
        """Receive input/resize from browser WebSocket and write to PTY."""
        try:
            while True:
                msg = await websocket.receive_text()
                # Check for resize control packet: {"type":"resize","cols":120,"rows":30}
                if msg.startswith("{") and '"type"' in msg and '"resize"' in msg:
                    try:
                        data = json.loads(msg)
                        if data.get("type") == "resize":
                            cols = int(data.get("cols", 80))
                            rows = int(data.get("rows", 24))
                            winsize = struct.pack("HHHH", rows, cols, 0, 0)
                            fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)
                            continue
                    except Exception:
                        pass

                # Normal terminal keystrokes / input
                os.write(master_fd, msg.encode("utf-8"))
        except (WebSocketDisconnect, asyncio.CancelledError):
            pass
        except Exception:
            pass

    task_pty_to_ws = asyncio.create_task(pty_to_ws())
    task_ws_to_pty = asyncio.create_task(ws_to_pty())

    try:
        done, pending = await asyncio.wait(
            [task_pty_to_ws, task_ws_to_pty],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for t in pending:
            t.cancel()
    finally:
        # Cleanup
        try:
            os.close(master_fd)
        except Exception:
            pass

        try:
            os.kill(pid, signal.SIGTERM)
            await asyncio.sleep(0.05)
            os.waitpid(pid, os.WNOHANG)
        except Exception:
            pass
