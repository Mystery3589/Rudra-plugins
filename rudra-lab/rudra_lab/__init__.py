"""rudra-lab plugin — disposable isolated lab environments."""

import os
import typer

# ── PATH normalisation ────────────────────────────────────────────────────────
# rudra (and pipx in general) can strip the user's PATH when loading plugins,
# causing shutil.which() to miss binaries that are clearly installed
# (e.g. /usr/bin/mitmdump, ~/.local/bin/node).  We patch os.environ["PATH"]
# once at import time so every subsequent which() call in this plugin sees the
# full standard search path.
_STANDARD_PATH_DIRS = [
    "/usr/local/sbin", "/usr/local/bin",
    "/usr/sbin",       "/usr/bin",
    "/sbin",           "/bin",
    str(os.path.expanduser("~/.local/bin")),
    str(os.path.expanduser("~/.cargo/bin")),
    str(os.path.expanduser("~/.nvm/bin")),
    "/usr/lib/mitmproxy/bin",
]

def _ensure_path() -> None:
    current = os.environ.get("PATH", "")
    existing = set(current.split(":"))

    # Also pick up active nvm node version if present
    nvm_versions = os.path.expanduser("~/.nvm/versions/node")
    if os.path.isdir(nvm_versions):
        for ver in sorted(os.listdir(nvm_versions), reverse=True):
            bin_dir = os.path.join(nvm_versions, ver, "bin")
            if os.path.isdir(bin_dir):
                _STANDARD_PATH_DIRS.append(bin_dir)
                break

    extras = [d for d in _STANDARD_PATH_DIRS if d not in existing and os.path.isdir(d)]
    if extras:
        os.environ["PATH"] = ":".join(extras) + (":" + current if current else "")

_ensure_path()
# ─────────────────────────────────────────────────────────────────────────────

from rudra_lab.commands import app
from rudra_lab.chaos import app as chaos_app

# Wire chaos command directly into the lab app
for _cmd in chaos_app.registered_commands:
    app.registered_commands.append(_cmd)


def register(main_app: typer.Typer) -> None:
    """Called by rudra at startup to register the lab command group."""
    main_app.add_typer(app, name="lab", help="Disposable isolated lab environments — sandbox anything safely.")
