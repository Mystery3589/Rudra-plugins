"""Shared helpers for rudra-lab: paths, config, isolation tier detection."""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

console = Console()

# ── Paths ─────────────────────────────────────────────────────────────────────

RUDRA_DIR   = Path.home() / ".rudra"
LAB_DIR     = RUDRA_DIR / "lab"
LABS_DIR    = LAB_DIR / "labs"       # one subdir per named lab
LOGS_DIR    = LAB_DIR / "logs"       # per-run logs
CONFIG_FILE = LAB_DIR / "config.toml"

for _d in (LABS_DIR, LOGS_DIR):
    _d.mkdir(parents=True, exist_ok=True)


# ── Isolation tiers ───────────────────────────────────────────────────────────

class Tier(str, Enum):
    DOCKER   = "docker"
    NSPAWN   = "nspawn"       # systemd-nspawn
    FIREJAIL = "firejail"
    UNSHARE  = "unshare"      # Linux user namespaces, no root
    ENV      = "env"          # venv + env-var isolation only (weakest)


TIER_DESCRIPTIONS = {
    Tier.DOCKER:   "Docker container — strongest isolation, network=none optional",
    Tier.NSPAWN:   "systemd-nspawn — OS-level namespace isolation",
    Tier.FIREJAIL: "firejail — seccomp + namespace sandbox, no root needed",
    Tier.UNSHARE:  "unshare — Linux user/pid/net namespaces, no root needed",
    Tier.ENV:      "env-only — venv + PATH + env-var isolation (weakest, always available)",
}

TIER_SAFETY = {
    Tier.DOCKER:   5,
    Tier.NSPAWN:   4,
    Tier.FIREJAIL: 4,
    Tier.UNSHARE:  3,
    Tier.ENV:      1,
}


def detect_tiers() -> list[Tier]:
    """Return available isolation tiers, best first."""
    available = []
    if shutil.which("docker"):
        try:
            r = subprocess.run(["docker", "info"], capture_output=True, timeout=3)
            if r.returncode == 0:
                available.append(Tier.DOCKER)
        except Exception:
            pass
    if shutil.which("systemd-nspawn"):
        available.append(Tier.NSPAWN)
    if shutil.which("firejail"):
        available.append(Tier.FIREJAIL)
    if shutil.which("unshare") and platform.system() == "Linux":
        available.append(Tier.UNSHARE)
    available.append(Tier.ENV)  # always available
    return available


def best_tier(prefer: Optional[str] = None) -> Tier:
    available = detect_tiers()
    if prefer:
        try:
            t = Tier(prefer)
            if t in available:
                return t
            console.print(f"[yellow]Tier '{prefer}' not available — using {available[0].value}.[/yellow]")
        except ValueError:
            console.print(f"[yellow]Unknown tier '{prefer}' — using {available[0].value}.[/yellow]")
    return available[0]


# ── Project type detection ────────────────────────────────────────────────────

class ProjectType(str, Enum):
    PYTHON = "python"
    NODE   = "node"
    RUST   = "rust"
    RUBY   = "ruby"
    GO     = "go"
    SHELL  = "shell"
    UNKNOWN = "unknown"


def detect_project_type(path: Path) -> ProjectType:
    markers = {
        ProjectType.PYTHON: ["pyproject.toml", "setup.py", "requirements.txt", "Pipfile"],
        ProjectType.NODE:   ["package.json", "node_modules"],
        ProjectType.RUST:   ["Cargo.toml"],
        ProjectType.RUBY:   ["Gemfile", ".ruby-version"],
        ProjectType.GO:     ["go.mod", "go.sum"],
        ProjectType.SHELL:  ["Makefile", "install.sh", "run.sh"],
    }
    for ptype, files in markers.items():
        if any((path / f).exists() for f in files):
            return ptype
    return ProjectType.UNKNOWN


# ── Lab config ────────────────────────────────────────────────────────────────

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        tomllib = None  # type: ignore

try:
    import tomli_w
    _HAS_TOMLI_W = True
except ImportError:
    _HAS_TOMLI_W = False


@dataclass
class LabConfig:
    name: str
    tier: str                            = Tier.ENV.value
    project_type: str                    = ProjectType.UNKNOWN.value
    source_path: str                     = ""
    created_at: str                      = field(default_factory=lambda: datetime.now().isoformat())
    disposable: bool                     = True   # auto-destroy after run
    network_isolated: bool               = True
    readonly_mounts: list[str]           = field(default_factory=list)
    writable_mounts: list[str]           = field(default_factory=list)
    env_vars: dict[str, str]             = field(default_factory=dict)
    port_bindings: list[str]             = field(default_factory=list)  # "host:container"
    docker_image: str                    = "ubuntu:22.04"
    docker_id: str                       = ""     # running container id
    nspawn_root: str                     = ""     # path to chroot dir
    last_run: str                        = ""
    run_count: int                       = 0
    status: str                          = "created"   # created|running|stopped|destroyed


def lab_config_path(name: str) -> Path:
    return LABS_DIR / name / "lab.toml"


def lab_dir(name: str) -> Path:
    return LABS_DIR / name


def load_lab(name: str) -> LabConfig:
    p = lab_config_path(name)
    if not p.exists():
        console.print(f"[bold red]Lab '{name}' not found.[/bold red]")
        console.print(f"[dim]Create it with: rudra lab create {name}[/dim]")
        raise typer.Exit(1)
    if tomllib is None:
        console.print("[red]tomllib not available — cannot read lab config.[/red]")
        raise typer.Exit(1)
    raw = tomllib.loads(p.read_text())
    lab_raw = raw.get("lab", raw)
    return LabConfig(**{k: v for k, v in lab_raw.items() if k in LabConfig.__dataclass_fields__})


def save_lab(cfg: LabConfig) -> None:
    d = lab_dir(cfg.name)
    d.mkdir(parents=True, exist_ok=True)
    p = lab_config_path(cfg.name)
    data = asdict(cfg)
    if _HAS_TOMLI_W:
        p.write_bytes(tomli_w.dumps({"lab": data}))
    else:
        # Fallback: write JSON-compatible TOML manually for simple types
        lines = ["[lab]\n"]
        for k, v in data.items():
            if isinstance(v, bool):
                lines.append(f'{k} = {"true" if v else "false"}\n')
            elif isinstance(v, int):
                lines.append(f"{k} = {v}\n")
            elif isinstance(v, str):
                escaped = v.replace('"', '\\"')
                lines.append(f'{k} = "{escaped}"\n')
            elif isinstance(v, list):
                items = ", ".join(f'"{x}"' for x in v)
                lines.append(f"{k} = [{items}]\n")
            elif isinstance(v, dict):
                if v:
                    lines.append(f"\n[lab.{k}]\n")
                    for dk, dv in v.items():
                        lines.append(f'{dk} = "{dv}"\n')
                else:
                    lines.append(f"[lab.{k}]\n")
        p.write_text("".join(lines))


def list_labs() -> list[LabConfig]:
    labs = []
    if not LABS_DIR.exists():
        return labs
    for d in sorted(LABS_DIR.iterdir()):
        if d.is_dir() and (d / "lab.toml").exists():
            try:
                labs.append(load_lab(d.name))
            except Exception:
                pass
    return labs


# ── Run logging ───────────────────────────────────────────────────────────────

def log_run(lab_name: str, cmd: str, output: str, exit_code: int) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOGS_DIR / f"{lab_name}_{ts}.log"
    log_file.write_text(
        f"Lab:       {lab_name}\n"
        f"Command:   {cmd}\n"
        f"Exit code: {exit_code}\n"
        f"Timestamp: {ts}\n"
        f"{'─' * 60}\n\n"
        f"{output}\n"
    )
    return log_file


# ── Shell helpers ─────────────────────────────────────────────────────────────

def capture(cmd: list[str], timeout: float = 30, env: dict | None = None) -> tuple[int, str]:
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            env={**os.environ, **(env or {})},
        )
        return r.returncode, (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return -1, f"(timed out after {timeout}s)"
    except FileNotFoundError as e:
        return -1, str(e)


def run_cmd(cmd: list[str], description: str | None = None,
            env: dict | None = None, check: bool = True) -> int:
    if description:
        console.print(f"[bold cyan]==> {description}[/bold cyan]")
    full_env = {**os.environ, **(env or {})}
    result = subprocess.run(cmd, env=full_env)
    if check and result.returncode != 0:
        console.print(f"[bold red]Command failed (exit {result.returncode})[/bold red]")
        raise typer.Exit(result.returncode)
    return result.returncode


def run_capture(cmd: list[str], description: str | None = None,
                env: dict | None = None, timeout: float = 300) -> tuple[int, str]:
    """Run and capture output, streaming to console in real time."""
    if description:
        console.print(f"[bold cyan]==> {description}[/bold cyan]")
    full_env = {**os.environ, **(env or {})}
    lines = []
    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, env=full_env,
        )
        for line in proc.stdout:  # type: ignore
            console.print(f"[dim]{line.rstrip()}[/dim]")
            lines.append(line)
        proc.wait(timeout=timeout)
        return proc.returncode, "".join(lines)
    except subprocess.TimeoutExpired:
        proc.kill()
        return -1, "".join(lines) + "\n(timed out)"
    except Exception as e:
        return -1, str(e)
