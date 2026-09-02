"""CLI command interface for Rudra Secret Safe."""

from __future__ import annotations

import getpass
import os
import subprocess
import sys
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from rudra_vault.crypto import (
    clear_session_key,
    get_cached_session_key,
    init_credentials,
    is_initialized,
    is_unlocked,
    verify_password,
)
from rudra_vault.storage import (
    add_file,
    add_note,
    add_secret,
    delete_item,
    get_item,
    get_item_data,
    get_vault_stats,
    list_items,
)

console = Console()
app = typer.Typer(
    name="vault",
    help="🔐 Secure encrypted Safe & Vault for passwords, API keys, documents, notes, photos, and videos.",
    no_args_is_help=False,
)

note_app = typer.Typer(help="📝 Manage confidential encrypted notes.", no_args_is_help=True)
secret_app = typer.Typer(help="🔑 Manage encrypted API keys & credentials.", no_args_is_help=True)
app.add_typer(note_app, name="note")
app.add_typer(secret_app, name="secret")


def _require_unlocked_key() -> bytes:
    key = get_cached_session_key()
    if key:
        return key

    if not is_initialized():
        console.print("[yellow]Vault is not initialized yet.[/yellow] Run: [bold cyan]rudra vault init[/bold cyan]")
        raise typer.Exit(code=1)

    console.print("[bold yellow]🔒 Vault is locked.[/bold yellow]")
    try:
        pw = getpass.getpass("Enter Vault Master Password: ")
    except (KeyboardInterrupt, EOFError):
        console.print("\n[dim]Aborted.[/dim]")
        raise typer.Exit(code=1)

    key = verify_password(pw)
    if not key:
        console.print("[bold red]✖ Incorrect master password.[/bold red]")
        raise typer.Exit(code=1)

    console.print("[bold green]✓ Vault unlocked for this session.[/bold green]\n")
    return key


@app.callback(invoke_without_command=True)
def vault_default(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        status_cmd()


# ── Initialization & Session ────────────────────────────────────────────────

@app.command(name="init")
def init_cmd():
    """Initialize a new encrypted secret safe with a master password."""
    if is_initialized():
        console.print("[yellow]Vault is already initialized.[/yellow]")
        console.print("To view stored assets, run: [bold cyan]rudra vault list[/bold cyan]")
        return

    console.print(
        Panel.fit(
            "[bold cyan]🔐 Rudra Secret Safe Initialization[/bold cyan]\n\n"
            "This will establish an AES-256-GCM encrypted locker for all your confidential\n"
            "passwords, API keys, documents, notes, photos, and videos.",
            border_style="cyan",
        )
    )

    try:
        p1 = getpass.getpass("Choose a strong Master Password: ")
        if not p1 or len(p1) < 6:
            console.print("[bold red]✖ Password must be at least 6 characters.[/bold red]")
            raise typer.Exit(code=1)

        p2 = getpass.getpass("Confirm Master Password: ")
        if p1 != p2:
            console.print("[bold red]✖ Passwords do not match.[/bold red]")
            raise typer.Exit(code=1)

        init_credentials(p1)
        console.print("\n[bold green]✓ Vault initialized successfully![/bold green]")
        console.print("[dim]Secrets and blobs will be encrypted at ~/.rudra/vault/[/dim]")
    except (KeyboardInterrupt, EOFError):
        console.print("\n[dim]Initialization cancelled.[/dim]")


@app.command(name="status")
def status_cmd():
    """Show safe status, lock state, and encrypted storage statistics."""
    stats = get_vault_stats()
    init_str = "[bold green]Initialized[/bold green]" if stats["initialized"] else "[bold yellow]Not Initialized[/bold yellow]"
    lock_str = "[bold green]Unlocked (Session Active)[/bold green]" if stats["unlocked"] else "[bold red]Locked[/bold red]"

    table = Table(show_header=False, box=None)
    table.add_row("[bold]Safe Status:[/bold]", init_str)
    table.add_row("[bold]Lock State:[/bold]", lock_str)
    table.add_row("[bold]Total Items:[/bold]", str(stats["total_items"]))
    table.add_row("[bold]Encrypted Storage:[/bold]", f"{stats['storage_mb']} MB ({stats['storage_bytes']} bytes)")

    console.print(
        Panel(
            table,
            title="🔐 Rudra Secret Safe Status",
            border_style="cyan" if stats["unlocked"] else "dim",
        )
    )
    if not stats["initialized"]:
        console.print("[dim]Run [bold cyan]rudra vault init[/bold cyan] to initialize your safe.[/dim]")


@app.command(name="unlock")
def unlock_cmd():
    """Unlock the vault for the current session."""
    _require_unlocked_key()


@app.command(name="lock")
def lock_cmd():
    """Lock the vault immediately and wipe decrypted session keys from RAM."""
    clear_session_key()
    console.print("[bold green]✓ Vault is now locked.[/bold green]")


# ── Files & Media (Images, Videos, Documents) ───────────────────────────────

@app.command(name="put")
def put_file_cmd(
    filepath: Annotated[Path, typer.Argument(help="Path to the file, photo, video, or document to encrypt.", exists=True, dir_okay=False)],
    name: Annotated[Optional[str], typer.Option("--name", "-n", help="Custom alias or filename inside the safe.")] = None,
    tag: Annotated[Optional[str], typer.Option("--tag", "-t", help="Tag or label to categorize this file.")] = None,
):
    """Encrypt and store any image, video, document, or file into the safe."""
    key = _require_unlocked_key()
    tags = [tag] if tag else []
    try:
        item = add_file(filepath, alias=name, tags=tags, key=key)
        console.print(f"[bold green]✓ Encrypted & locked into safe:[/bold green] [cyan]{item['name']}[/cyan] ({item['preview']})")
        console.print(f"  [dim]Type: {item['type']} | MIME: {item['mime_type']} | ID: {item['id'][:8]}...[/dim]")
    except Exception as e:
        console.print(f"[bold red]✖ Failed to store file: {e}[/bold red]")


@app.command(name="get")
def get_file_cmd(
    name_or_id: Annotated[str, typer.Argument(help="Filename or item ID of the asset to decrypt.")],
    output: Annotated[Optional[Path], typer.Option("--output", "-o", help="Destination path to save the decrypted file.")] = None,
):
    """Decrypt and extract a file, image, or document from the safe."""
    key = _require_unlocked_key()
    try:
        item, data = get_item_data(name_or_id, key=key)
        dest = output or Path(item["name"])
        dest.write_bytes(data)
        console.print(f"[bold green]✓ Decrypted & saved:[/bold green] [cyan]{dest}[/cyan] ({round(len(data) / 1024, 1)} KB)")
    except Exception as e:
        console.print(f"[bold red]✖ Decryption failed: {e}[/bold red]")


# ── Secure Notes ────────────────────────────────────────────────────────────

@note_app.command(name="create")
def note_create_cmd(
    title: Annotated[str, typer.Argument(help="Title of the confidential note.")],
    content: Annotated[Optional[str], typer.Option("--content", "-c", help="Note body text (opens editor if omitted).")] = None,
    tag: Annotated[Optional[str], typer.Option("--tag", "-t", help="Tag for this note.")] = None,
):
    """Create a confidential encrypted note."""
    key = _require_unlocked_key()
    body = content
    if not body:
        console.print(f"Enter note content for [cyan]{title}[/cyan] (press Ctrl+D when finished):")
        try:
            body = sys.stdin.read()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Aborted.[/dim]")
            return

    if not body.strip():
        console.print("[yellow]Empty note not saved.[/yellow]")
        return

    item = add_note(title, body, tags=[tag] if tag else ["note"], key=key)
    console.print(f"[bold green]✓ Encrypted note saved:[/bold green] [cyan]{item['name']}[/cyan]")


@note_app.command(name="read")
def note_read_cmd(
    name_or_id: Annotated[str, typer.Argument(help="Note title or item ID.")],
):
    """Decrypt and read a confidential note."""
    key = _require_unlocked_key()
    try:
        item, data = get_item_data(name_or_id, key=key)
        text = data.decode("utf-8", errors="replace")
        console.print(
            Panel(
                text,
                title=f"📝 {item['name']}",
                subtitle=f"Created: {item['created_at']}",
                border_style="cyan",
            )
        )
    except Exception as e:
        console.print(f"[bold red]✖ Failed to read note: {e}[/bold red]")


# ── Secrets & Passwords ─────────────────────────────────────────────────────

@secret_app.command(name="set")
def secret_set_cmd(
    name: Annotated[str, typer.Argument(help="Key name (e.g. OPENAI_API_KEY, DB_PASSWORD).")],
    value: Annotated[Optional[str], typer.Argument(help="Secret value (prompted securely if omitted).")] = None,
    category: Annotated[str, typer.Option("--category", "-c", help="Category (api_key, token, password, etc.).")] = "api_key",
):
    """Store an encrypted API key, token, or password."""
    key = _require_unlocked_key()
    val = value
    if not val:
        try:
            val = getpass.getpass(f"Enter secret value for {name}: ")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Aborted.[/dim]")
            return

    if not val:
        console.print("[yellow]Empty value not stored.[/yellow]")
        return

    item = add_secret(name, val, category=category, key=key)
    console.print(f"[bold green]✓ Secret encrypted & stored:[/bold green] [cyan]{item['name']}[/cyan] ({item['category']})")


@secret_app.command(name="get")
def secret_get_cmd(
    name: Annotated[str, typer.Argument(help="Key name to retrieve.")],
    clip: Annotated[bool, typer.Option("--clip", "-c", help="Copy secret value to clipboard instead of printing.")] = False,
):
    """Decrypt and retrieve a secret value."""
    key = _require_unlocked_key()
    try:
        item, data = get_item_data(name, key=key)
        val = data.decode("utf-8", errors="replace")
        if clip:
            try:
                import shutil
                if shutil.which("xclip"):
                    proc = subprocess.Popen(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE)
                    proc.communicate(data)
                    console.print("[bold green]✓ Secret copied to clipboard via xclip![/bold green]")
                    return
                elif shutil.which("wl-copy"):
                    proc = subprocess.Popen(["wl-copy"], stdin=subprocess.PIPE)
                    proc.communicate(data)
                    console.print("[bold green]✓ Secret copied to clipboard via wl-copy![/bold green]")
                    return
            except Exception:
                pass
        console.print(f"[cyan]{item['name']}:[/cyan] [bold white]{val}[/bold white]")
    except Exception as e:
        console.print(f"[bold red]✖ Failed to retrieve secret: {e}[/bold red]")


# ── Catalog & Deletion ──────────────────────────────────────────────────────

@app.command(name="list")
def list_cmd(
    filter_type: Annotated[Optional[str], typer.Option("--type", "-t", help="Filter by item type: secret, note, media, document.")] = None,
):
    """List all encrypted assets stored in your safe."""
    key = _require_unlocked_key()
    try:
        items = list_items(filter_type=filter_type, key=key)
        if not items:
            console.print("[yellow]Safe is currently empty.[/yellow] Use [bold cyan]rudra vault put[/bold cyan], [bold cyan]rudra vault note create[/bold cyan], or [bold cyan]rudra vault secret set[/bold cyan] to add items.")
            return

        table = Table(title=f"🔐 Rudra Secret Safe ({len(items)} Items)", border_style="cyan")
        table.add_column("Type", style="bold")
        table.add_column("Name / Key", style="cyan")
        table.add_column("MIME / Format", style="dim")
        table.add_column("Size", justify="right", style="green")
        table.add_column("Created", style="dim")

        type_icons = {
            "media": "🖼️ media",
            "document": "📄 document",
            "note": "📝 note",
            "secret": "🔑 secret",
        }

        for item in items:
            itype = type_icons.get(item.get("type", ""), item.get("type", ""))
            sz = f"{round(item.get('size_bytes', 0) / 1024, 1)} KB" if item.get("size_bytes", 0) >= 1024 else f"{item.get('size_bytes', 0)} B"
            table.add_row(
                itype,
                item["name"],
                item.get("mime_type", "—"),
                sz,
                item.get("created_at", "—"),
            )

        console.print(table)
    except Exception as e:
        console.print(f"[bold red]✖ Failed to list vault items: {e}[/bold red]")


@app.command(name="rm")
def rm_cmd(
    name_or_id: Annotated[str, typer.Argument(help="Filename, key, or item ID to delete.")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation prompt.")] = False,
):
    """Delete an item and permanently purge its encrypted blob from disk."""
    key = _require_unlocked_key()
    if not yes:
        confirm = typer.confirm(f"Are you sure you want to permanently delete '{name_or_id}'?")
        if not confirm:
            console.print("[dim]Cancelled.[/dim]")
            return

    ok = delete_item(name_or_id, key=key)
    if ok:
        console.print(f"[bold green]✓ Purged item from safe:[/bold green] [cyan]{name_or_id}[/cyan]")
    else:
        console.print(f"[bold red]✖ Item '{name_or_id}' not found in safe.[/bold red]")
