"""FastAPI Web Server for Rudra Web UI."""

from __future__ import annotations

import json
import os
import platform
import webbrowser
from pathlib import Path
from typing import Optional

import typer
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from rich.console import Console
from rich.panel import Panel

try:
    from rudra.web.auth import get_server_token, set_server_token, verify_token, is_local_client
    from rudra.web.history import clear_history, load_history
    from rudra.web.runner import stream_command
    from rudra.web.schema import get_rudra_schema
    from rudra.web.sudo import has_nopasswd_sudo, set_cached_sudo_password
except ImportError:
    from rudra_web.auth import get_server_token, set_server_token, verify_token, is_local_client
    from rudra_web.history import clear_history, load_history
    from rudra_web.runner import stream_command
    from rudra_web.schema import get_rudra_schema
    from rudra_web.sudo import has_nopasswd_sudo, set_cached_sudo_password

console = Console()
STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Rudra Web UI", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SudoAuthRequest(BaseModel):
    password: str


class CommandRunRequest(BaseModel):
    args: list[str]


# ── Static UI Routes ─────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
@app.get("/history", response_class=HTMLResponse)
async def serve_index():
    index_path = STATIC_DIR / "index.html"
    return FileResponse(index_path)


# ── REST API Endpoints ───────────────────────────────────────────────────────

@app.get("/api/status")
async def get_system_status(req: Request):
    client_host = req.client.host if req.client else None
    is_local = is_local_client(client_host)
    return {
        "os": platform.system(),
        "platform_release": platform.release(),
        "machine": platform.machine(),
        "has_nopasswd_sudo": has_nopasswd_sudo(),
        "is_local": is_local,
        "auth_required": not is_local,
    }


@app.get("/api/schema")
async def get_schema(_: bool = Depends(verify_token)):
    """Return the live Click/Typer introspected command tree."""
    return get_rudra_schema()


@app.get("/api/history")
async def get_history_api(_: bool = Depends(verify_token)):
    """Return auto-pruned history records (max 100 entries / last 7 days)."""
    return load_history()


@app.delete("/api/history")
async def delete_history_api(_: bool = Depends(verify_token)):
    clear_history()
    return {"status": "success", "message": "History cleared"}


@app.post("/api/sudo-auth")
async def authenticate_sudo(payload: SudoAuthRequest, _: bool = Depends(verify_token)):
    """Hold sudo password in memory for elevated operations."""
    ok = set_cached_sudo_password(payload.password)
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid sudo password")
    return {"status": "success", "message": "Sudo privileges cached in RAM for session"}


# ── WebSocket Command Streaming ─────────────────────────────────────────────

@app.websocket("/ws/run")
async def websocket_run_command(websocket: WebSocket):
    await websocket.accept()

    # Authenticate remote connections
    client_host = websocket.client.host if websocket.client else None
    if not is_local_client(client_host):
        token = websocket.query_params.get("token")
        if not token or token != get_server_token():
            await websocket.send_json({"type": "error", "data": "Unauthorized connection"})
            await websocket.close(code=1008)
            return

    try:
        data_text = await websocket.receive_text()
        data = json.loads(data_text)
        args = data.get("args", [])

        if not args:
            await websocket.send_json({"type": "error", "data": "No command arguments provided"})
            await websocket.close()
            return

        async for event in stream_command(args):
            await websocket.send_json(event)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "data": f"Internal execution error: {e}"})
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


# Mount static assets (Vite /assets & /static)
assets_dir = STATIC_DIR / "assets"
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ── CLI Command: rudra web serve ────────────────────────────────────────────

web_cli_app = typer.Typer(name="web", help="🌐 Rudra Terminal Web UI Server.", no_args_is_help=True)


@web_cli_app.command(name="serve")
def serve(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Bind IP address (127.0.0.1 for local, 0.0.0.0 for network access)."),
    port: int = typer.Option(7070, "--port", "-p", help="Port to listen on."),
    token: Optional[str] = typer.Option(None, "--token", "-t", help="Custom auth token for remote connections."),
    no_browser: bool = typer.Option(False, "--no-browser", help="Do not automatically open browser on startup."),
):
    """Start the Rudra Terminal Web UI server."""
    if token:
        set_server_token(token)
    active_token = get_server_token()

    is_remote = host not in ("127.0.0.1", "localhost")
    url = f"http://{host}:{port}"
    local_url = f"http://localhost:{port}"

    console.print(
        Panel.fit(
            f"[bold cyan]🔱 Rudra Terminal Web UI Server[/bold cyan]\n\n"
            f"[bold green]▶ Running at:[/bold green] [underline cyan]{url}[/underline cyan]\n"
            + (f"[bold yellow]🔑 Remote Auth Token:[/bold yellow] [bold white]{active_token}[/bold white]\n" if is_remote else "[dim]Localhost mode: Authentication bypassed for local browser[/dim]\n")
            + f"[dim]Press Ctrl+C to terminate the server[/dim]",
            border_style="cyan",
        )
    )

    if not no_browser and not is_remote:
        try:
            webbrowser.open(local_url)
        except Exception:
            pass

    uvicorn.run(app, host=host, port=port, log_level="warning")
