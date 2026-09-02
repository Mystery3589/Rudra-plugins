"""Language-level environment bootstrapping inside a lab.

Each setup_* function prepares the source scratch copy (already on the host,
at ~/.rudra/lab/labs/<name>/src_copy/) so it is ready to run inside nspawn.
Because the scratch copy is a plain writable directory on the host, bootstrap
steps (npm install, pip install, etc.) run directly on it — no container
needed.  The container then gets this already-prepared directory as a plain
writable --bind mount.

Rules:
  - NEVER run install scripts (--ignore-scripts for npm, no postinstall hooks).
    Scripts belong inside the sandboxed container, not on the host.
  - All writes go into the scratch copy, never into the original source.
  - bootstrap_env returns a dict of extra env vars to inject into the container.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Optional

from rich.console import Console

from rudra_lab.helpers import LabConfig, ProjectType, run_cmd

console = Console()


def _scratch_src(cfg: LabConfig) -> Optional[Path]:
    """Return the src_copy path if it exists."""
    p = Path.home() / ".rudra" / "lab" / "labs" / cfg.name / "src_copy"
    return p if p.exists() else None


# ── per-language setup ────────────────────────────────────────────────────────

def setup_python(cfg: LabConfig, source_path: Path) -> dict[str, str]:
    venv = Path.home() / ".rudra" / "lab" / "labs" / cfg.name / "venv"
    if not (venv / "bin" / "python").exists():
        python = shutil.which("python3") or "python3"
        run_cmd([python, "-m", "venv", str(venv)], "Creating isolated venv")

    pip = str(venv / "bin" / "pip")
    env = {
        "VIRTUAL_ENV": str(venv),
        "PATH": f"{venv / 'bin'}:{os.environ.get('PATH', '')}",
        "PYTHONPATH": "",
    }
    for req in ("requirements.txt", "requirements-dev.txt"):
        rp = source_path / req
        if rp.exists():
            run_cmd([pip, "install", "-r", str(rp), "--quiet"], f"Installing {req}")
    if (source_path / "pyproject.toml").exists():
        run_cmd([pip, "install", "-e", str(source_path), "--quiet"], "Installing package")
    return env


def setup_node(cfg: LabConfig, source_path: Path) -> dict[str, str]:
    """Install node_modules into the scratch copy without running any scripts."""
    if not (source_path / "package.json").exists():
        return {}

    npm = shutil.which("npm") or "npm"
    run_cmd(
        [npm, "install", "--prefix", str(source_path), "--ignore-scripts"],
        "Installing node_modules",
    )
    return {}


def setup_rust(cfg: LabConfig, source_path: Path) -> dict[str, str]:
    cargo_home = Path.home() / ".rudra" / "lab" / "labs" / cfg.name / "cargo"
    cargo_home.mkdir(parents=True, exist_ok=True)
    env = {
        "CARGO_HOME": str(cargo_home),
        "CARGO_TARGET_DIR": str(cargo_home / "target"),
        "PATH": f"{cargo_home / 'bin'}:{os.environ.get('PATH', '')}",
    }
    if shutil.which("cargo") and (source_path / "Cargo.toml").exists():
        run_cmd(["cargo", "fetch", "--manifest-path", str(source_path / "Cargo.toml")],
                "Fetching crates", env=env)
    return env


def setup_ruby(cfg: LabConfig, source_path: Path) -> dict[str, str]:
    gem_home = Path.home() / ".rudra" / "lab" / "labs" / cfg.name / "gems"
    gem_home.mkdir(parents=True, exist_ok=True)
    env = {
        "GEM_HOME": str(gem_home),
        "GEM_PATH": str(gem_home),
        "BUNDLE_PATH": str(gem_home),
        "PATH": f"{gem_home / 'bin'}:{os.environ.get('PATH', '')}",
    }
    if (source_path / "Gemfile").exists() and shutil.which("bundle"):
        run_cmd(["bundle", "install", "--path", str(gem_home)], "Installing gems", env=env)
    return env


def setup_go(cfg: LabConfig, source_path: Path) -> dict[str, str]:
    gopath = Path.home() / ".rudra" / "lab" / "labs" / cfg.name / "gopath"
    gopath.mkdir(parents=True, exist_ok=True)
    env = {
        "GOPATH": str(gopath),
        "GOCACHE": str(gopath / "cache"),
        "PATH": f"{gopath / 'bin'}:{os.environ.get('PATH', '')}",
    }
    if shutil.which("go") and (source_path / "go.mod").exists():
        run_cmd(["go", "mod", "download"], "Downloading Go modules", env={**os.environ, **env})
    return env


# ── dispatch ──────────────────────────────────────────────────────────────────

_SETUP_FNS = {
    ProjectType.PYTHON: setup_python,
    ProjectType.NODE:   setup_node,
    ProjectType.RUST:   setup_rust,
    ProjectType.RUBY:   setup_ruby,
    ProjectType.GO:     setup_go,
}


def bootstrap_env(cfg: LabConfig) -> dict[str, str]:
    """
    Prepare the language environment in the lab's src_copy scratch dir.
    Returns extra env vars to inject into the container.
    """
    if not cfg.source_path:
        return {}

    # Bootstrap runs against the scratch copy if it exists, otherwise original.
    # unshare.py's _prepare_nspawn_src() creates the copy before bootstrap_env
    # is called for nspawn runs.  For other tiers the original is used.
    scratch = Path.home() / ".rudra" / "lab" / "labs" / cfg.name / "src_copy"
    source = scratch if scratch.exists() else Path(cfg.source_path)

    if not source.exists():
        console.print(f"[yellow]Source '{source}' not found — skipping bootstrap.[/yellow]")
        return {}

    try:
        ptype = ProjectType(cfg.project_type)
    except ValueError:
        ptype = ProjectType.UNKNOWN

    fn = _SETUP_FNS.get(ptype)
    if fn is None:
        return {}

    console.print(f"[dim]Bootstrapping {ptype.value} environment...[/dim]")
    try:
        return fn(cfg, source)
    except Exception as e:
        console.print(f"[yellow]Bootstrap warning: {e}[/yellow]")
        return {}
