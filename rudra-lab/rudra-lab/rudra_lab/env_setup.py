"""Language-level environment bootstrapping inside a lab.

Sets up the right language toolchain inside the lab directory:
  Python  → venv
  Node    → local node_modules / nvm shim
  Rust    → cargo toolchain override
  Ruby    → bundler install
  Go      → GOPATH isolation
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from rich.console import Console

from rudra_lab.helpers import LabConfig, ProjectType, capture, run_cmd

console = Console()


def _lab_venv(cfg: LabConfig) -> Path:
    from rudra_lab.helpers import lab_dir
    return lab_dir(cfg.name) / "venv"


def setup_python(cfg: LabConfig, source_path: Path) -> dict[str, str]:
    """Create an isolated venv and install requirements."""
    venv = _lab_venv(cfg)
    env_extra: dict[str, str] = {}

    if not venv.exists():
        python = shutil.which("python3") or "python3"
        run_cmd([python, "-m", "venv", str(venv)], "Creating isolated venv")

    pip = str(venv / "bin" / "pip")
    env_extra["VIRTUAL_ENV"]    = str(venv)
    env_extra["PATH"]           = f"{venv/'bin'}:{os.environ.get('PATH','')}"
    env_extra["PYTHONPATH"]     = ""   # clear any host PYTHONPATH

    # Install deps
    for req_file in ("requirements.txt", "requirements-dev.txt"):
        rp = source_path / req_file
        if rp.exists():
            run_cmd([pip, "install", "-r", str(rp), "--quiet"], f"Installing {req_file}")

    pyproject = source_path / "pyproject.toml"
    if pyproject.exists():
        run_cmd([pip, "install", "-e", str(source_path), "--quiet"], "Installing package (editable)")

    return env_extra


def setup_node(cfg: LabConfig, source_path: Path) -> dict[str, str]:
    """Isolated node_modules in the lab dir, not system-wide."""
    from rudra_lab.helpers import lab_dir
    node_home = lab_dir(cfg.name) / "node"
    node_home.mkdir(parents=True, exist_ok=True)

    env_extra: dict[str, str] = {
        "NPM_CONFIG_PREFIX": str(node_home),
        "NODE_PATH":         str(node_home / "lib" / "node_modules"),
        "PATH":              f"{node_home/'bin'}:{os.environ.get('PATH','')}",
    }

    pkg_json = source_path / "package.json"
    if pkg_json.exists():
        npm = shutil.which("npm") or "npm"
        run_cmd(
            [npm, "install", "--prefix", str(source_path)],
            "Installing node_modules",
            env=env_extra,
        )

    return env_extra


def setup_rust(cfg: LabConfig, source_path: Path) -> dict[str, str]:
    """Isolated CARGO_HOME and RUSTUP_HOME inside lab dir."""
    from rudra_lab.helpers import lab_dir
    cargo_home  = lab_dir(cfg.name) / "cargo"
    rustup_home = lab_dir(cfg.name) / "rustup"
    cargo_home.mkdir(parents=True, exist_ok=True)
    rustup_home.mkdir(parents=True, exist_ok=True)

    env_extra: dict[str, str] = {
        "CARGO_HOME":  str(cargo_home),
        "RUSTUP_HOME": str(rustup_home),
        "PATH":        f"{cargo_home/'bin'}:{os.environ.get('PATH','')}",
    }

    # Ensure the toolchain is fetched
    if shutil.which("cargo"):
        cargo_toml = source_path / "Cargo.toml"
        if cargo_toml.exists():
            run_cmd(
                ["cargo", "fetch", "--manifest-path", str(cargo_toml)],
                "Fetching crates",
                env=env_extra,
            )

    return env_extra


def setup_ruby(cfg: LabConfig, source_path: Path) -> dict[str, str]:
    from rudra_lab.helpers import lab_dir
    gem_home = lab_dir(cfg.name) / "gems"
    gem_home.mkdir(parents=True, exist_ok=True)

    env_extra: dict[str, str] = {
        "GEM_HOME": str(gem_home),
        "GEM_PATH": str(gem_home),
        "PATH":     f"{gem_home/'bin'}:{os.environ.get('PATH','')}",
    }

    gemfile = source_path / "Gemfile"
    if gemfile.exists() and shutil.which("bundle"):
        run_cmd(
            ["bundle", "install", "--path", str(gem_home)],
            "Installing gems",
            env=env_extra,
        )

    return env_extra


def setup_go(cfg: LabConfig, source_path: Path) -> dict[str, str]:
    from rudra_lab.helpers import lab_dir
    gopath = lab_dir(cfg.name) / "gopath"
    gopath.mkdir(parents=True, exist_ok=True)

    env_extra: dict[str, str] = {
        "GOPATH": str(gopath),
        "PATH":   f"{gopath/'bin'}:{os.environ.get('PATH','')}",
    }

    go_mod = source_path / "go.mod"
    if go_mod.exists() and shutil.which("go"):
        run_cmd(
            ["go", "mod", "download"],
            "Downloading Go modules",
            env={**os.environ, **env_extra},
        )

    return env_extra


def bootstrap_env(cfg: LabConfig) -> dict[str, str]:
    """Auto-detect project type and bootstrap the right language env.
    Returns a dict of extra env vars to inject into the lab run."""
    if not cfg.source_path:
        return {}

    source = Path(cfg.source_path)
    if not source.exists():
        console.print(f"[yellow]Source path '{source}' not found — skipping env bootstrap.[/yellow]")
        return {}

    ptype = ProjectType(cfg.project_type) if cfg.project_type else ProjectType.UNKNOWN
    console.print(f"[dim]Bootstrapping {ptype.value} environment...[/dim]")

    try:
        if ptype == ProjectType.PYTHON:
            return setup_python(cfg, source)
        elif ptype == ProjectType.NODE:
            return setup_node(cfg, source)
        elif ptype == ProjectType.RUST:
            return setup_rust(cfg, source)
        elif ptype == ProjectType.RUBY:
            return setup_ruby(cfg, source)
        elif ptype == ProjectType.GO:
            return setup_go(cfg, source)
        else:
            return {}
    except Exception as e:
        console.print(f"[yellow]Env bootstrap warning: {e}[/yellow]")
        return {}
