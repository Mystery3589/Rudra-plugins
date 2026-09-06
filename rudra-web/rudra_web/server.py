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
from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
    Depends,
    HTTPException,
    Request,
    Response,
    UploadFile,
    File,
    Form,
)
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
    from rudra.web.api import (
        get_system_stats,
        list_system_services,
        get_security_overview,
        list_lab_environments,
        list_osint_reports,
        get_rudra_commands,
        get_logs,
    )
except ImportError:
    from rudra_web.auth import get_server_token, set_server_token, verify_token, is_local_client
    from rudra_web.history import clear_history, load_history
    from rudra_web.runner import stream_command
    from rudra_web.schema import get_rudra_schema
    from rudra_web.sudo import has_nopasswd_sudo, set_cached_sudo_password
    from rudra_web.api import (
        get_system_stats,
        list_system_services,
        get_security_overview,
        list_lab_environments,
        list_osint_reports,
        get_rudra_commands,
        get_logs,
    )

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


class VaultAuthRequest(BaseModel):
    password: str


class VaultNoteRequest(BaseModel):
    title: str
    content: str
    tags: list[str] = []


class VaultSecretRequest(BaseModel):
    name: str
    value: str
    category: str = "api_key"
    tags: list[str] = []


# ── Static UI Routes ─────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
@app.get("/history", response_class=HTMLResponse)
async def serve_index():
    index_path = STATIC_DIR / "index.html"
    return FileResponse(index_path)


@app.get("/terminal", response_class=HTMLResponse)
async def serve_terminal():
    """Interactive full-screen xterm.js terminal page."""
    try:
        from rudra.web.terminal_html import TERMINAL_PAGE_HTML
    except ImportError:
        from rudra_web.terminal_html import TERMINAL_PAGE_HTML
    return HTMLResponse(TERMINAL_PAGE_HTML)


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


@app.get("/api/stats")
async def get_stats():
    """Return live system stats: CPU load, RAM, disk, uptime."""
    return get_system_stats()


@app.get("/api/services")
async def get_services(limit: int = 50):
    """Return list of systemd services."""
    return list_system_services(limit=limit)


@app.get("/api/security")
async def get_security():
    """Return security posture overview."""
    return get_security_overview()


@app.get("/api/labs")
async def get_labs():
    """Return list of Rudra Lab environments."""
    return list_lab_environments()


@app.get("/api/osint")
async def get_osint():
    """Return list of saved OSINT investigation dossiers."""
    return list_osint_reports()


@app.get("/api/commands")
async def get_commands():
    """Return catalog of Rudra commands."""
    return get_rudra_commands()


@app.get("/api/logs")
async def get_system_logs():
    """Return web server and system journal logs."""
    return get_logs()


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


# ── Vault / Secret Safe Endpoints ───────────────────────────────────────────

@app.get("/api/vault/status")
async def get_safe_status():
    """Return vault status, initialization state, drive status, and storage metrics."""
    try:
        from rudra_vault.storage import get_vault_stats
        from rudra_vault.drive import get_drive_status
        stats = get_vault_stats()
        stats["drive"] = get_drive_status()
        return stats
    except Exception as e:
        return {"initialized": False, "unlocked": False, "total_items": 0, "storage_mb": 0.0, "error": str(e)}


@app.post("/api/vault/init")
async def init_safe(payload: VaultAuthRequest):
    """Initialize safe with master password."""
    try:
        from rudra_vault.crypto import init_credentials, is_initialized
        if is_initialized():
            raise HTTPException(status_code=400, detail="Vault is already initialized")
        if len(payload.password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        init_credentials(payload.password)
        return {"status": "success", "message": "Vault initialized and unlocked"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/vault/unlock")
async def unlock_safe(payload: VaultAuthRequest):
    """Unlock safe with master password for the current session."""
    try:
        from rudra_vault.crypto import verify_password
        key = verify_password(payload.password)
        if not key:
            raise HTTPException(status_code=400, detail="Incorrect master password")
        return {"status": "success", "message": "Vault unlocked"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/vault/lock")
async def lock_safe():
    """Lock safe immediately, sync and wipe daily drive."""
    try:
        from rudra_vault.crypto import clear_session_key, get_cached_session_key
        from rudra_vault.drive import is_drive_mounted, unmount_drive
        key = get_cached_session_key()
        if is_drive_mounted():
            unmount_drive(key=key, wipe=True)
        clear_session_key()
        return {"status": "success", "message": "Vault locked"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/vault/drive/mount")
async def mount_drive_endpoint():
    """Mount and decrypt daily drive into ~/Vault."""
    try:
        from rudra_vault.crypto import get_cached_session_key
        from rudra_vault.drive import mount_drive
        key = get_cached_session_key()
        if not key:
            raise HTTPException(status_code=401, detail="Vault is locked")
        res = mount_drive(key)
        return res
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/vault/drive/sync")
async def sync_drive_endpoint():
    """Sync changes from ~/Vault back into the safe."""
    try:
        from rudra_vault.crypto import get_cached_session_key
        from rudra_vault.drive import sync_drive_to_vault, is_drive_mounted
        if not is_drive_mounted():
            raise HTTPException(status_code=400, detail="Daily drive is not mounted")
        key = get_cached_session_key()
        if not key:
            raise HTTPException(status_code=401, detail="Vault is locked")
        res = sync_drive_to_vault(key)
        return {"status": "ok", "sync": res}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/vault/items")
async def get_safe_items(type: Optional[str] = None):
    """List encrypted items in safe."""
    try:
        from rudra_vault.storage import list_items
        return list_items(filter_type=type)
    except PermissionError:
        raise HTTPException(status_code=401, detail="Vault is locked")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/vault/upload")
async def upload_safe_file(
    file: UploadFile = File(...),
    alias: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
):
    """Encrypt and store an uploaded file (image, video, document, etc.) into the safe."""
    try:
        from rudra_vault.storage import add_file_bytes
        data = await file.read()
        filename = alias or file.filename or "unnamed_file"
        tag_list = [t.strip() for t in tags.split(",")] if tags else None
        item = add_file_bytes(data=data, filename=filename, mime_type=file.content_type, tags=tag_list)
        return item
    except PermissionError:
        raise HTTPException(status_code=401, detail="Vault is locked")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/vault/blob/{item_id}")
async def get_safe_blob(item_id: str):
    """Stream decrypted media/file directly to browser for inline display or playback."""
    try:
        from rudra_vault.storage import get_item_data
        item, data = get_item_data(item_id)
        return Response(
            content=data,
            media_type=item.get("mime_type", "application/octet-stream"),
            headers={"Content-Disposition": f"inline; filename=\"{item.get('name', 'file')}\""}
        )
    except PermissionError:
        raise HTTPException(status_code=401, detail="Vault is locked")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Item not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/vault/download/{item_id}")
async def download_safe_file(item_id: str):
    """Download decrypted original file."""
    try:
        from rudra_vault.storage import get_item_data
        item, data = get_item_data(item_id)
        return Response(
            content=data,
            media_type=item.get("mime_type", "application/octet-stream"),
            headers={"Content-Disposition": f"attachment; filename=\"{item.get('name', 'file')}\""}
        )
    except PermissionError:
        raise HTTPException(status_code=401, detail="Vault is locked")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Item not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/vault/note")
async def save_safe_note(payload: VaultNoteRequest):
    """Save an encrypted confidential note."""
    try:
        from rudra_vault.storage import add_note
        item = add_note(title=payload.title, content=payload.content, tags=payload.tags)
        return item
    except PermissionError:
        raise HTTPException(status_code=401, detail="Vault is locked")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/vault/note/{item_id}")
async def read_safe_note(item_id: str):
    """Read a decrypted note content."""
    try:
        from rudra_vault.storage import get_item_data
        item, data = get_item_data(item_id)
        return {"id": item["id"], "name": item["name"], "content": data.decode("utf-8", errors="replace")}
    except PermissionError:
        raise HTTPException(status_code=401, detail="Vault is locked")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Note not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/vault/secret")
async def save_safe_secret(payload: VaultSecretRequest):
    """Store an encrypted API key or credential."""
    try:
        from rudra_vault.storage import add_secret
        item = add_secret(name=payload.name, value=payload.value, category=payload.category, tags=payload.tags)
        return item
    except PermissionError:
        raise HTTPException(status_code=401, detail="Vault is locked")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/vault/secret/{item_id}")
async def reveal_safe_secret(item_id: str):
    """Decrypt and reveal secret value."""
    try:
        from rudra_vault.storage import get_item_data
        item, data = get_item_data(item_id)
        return {"id": item["id"], "name": item["name"], "value": data.decode("utf-8", errors="replace")}
    except PermissionError:
        raise HTTPException(status_code=401, detail="Vault is locked")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Secret not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/vault/item/{item_id}")
async def delete_safe_item(item_id: str):
    """Permanently delete an item from the safe."""
    try:
        from rudra_vault.storage import delete_item
        ok = delete_item(item_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Item not found")
        return {"status": "success", "message": "Item deleted"}
    except PermissionError:
        raise HTTPException(status_code=401, detail="Vault is locked")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



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


@app.websocket("/ws/terminal")
async def websocket_terminal(websocket: WebSocket):
    """Interactive full-shell PTY WebSocket connection."""
    client_host = websocket.client.host if websocket.client else None
    if not is_local_client(client_host):
        token = websocket.query_params.get("token")
        if not token or token != get_server_token():
            await websocket.close(code=1008)
            return

    try:
        from rudra.web.terminal import handle_terminal_websocket
    except ImportError:
        from rudra_web.terminal import handle_terminal_websocket

    await handle_terminal_websocket(websocket)


# ── Theme API Endpoints ─────────────────────────────────────────────────────

@app.get("/api/theme")
async def get_theme_endpoint():
    """Return currently active theme palette."""
    from rudra.theme import get_current_theme
    return get_current_theme().to_dict()


@app.get("/api/theme/list")
async def list_themes_endpoint():
    """Return all available themes."""
    try:
        from rudra_theme.manager import get_available_themes
        themes = get_available_themes()
        return {name: t.to_dict() for name, t in themes.items()}
    except Exception:
        from rudra.theme import get_current_theme
        t = get_current_theme()
        return {t.name: t.to_dict()}


@app.post("/api/theme/set")
async def set_theme_endpoint(req: dict):
    """Set active theme."""
    name = req.get("name", "").strip().lower()
    if not name:
        raise HTTPException(status_code=400, detail="Theme name required")
    try:
        from rudra_theme.manager import set_active_theme
        if set_active_theme(name):
            from rudra.theme import get_current_theme
            return {"status": "ok", "theme": get_current_theme().to_dict()}
        raise HTTPException(status_code=404, detail=f"Theme '{name}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
