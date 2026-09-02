"""Non-Docker isolation backends: unshare, firejail, systemd-nspawn."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from rich.console import Console

from rudra_lab.helpers import LabConfig, capture

console = Console()


# ── unshare ───────────────────────────────────────────────────────────────────

def _unshare_prefix(cfg: LabConfig) -> list[str]:
    """Build an `unshare` command prefix for namespace isolation."""
    args = ["unshare"]
    args += ["--user"]       # user namespace (no root needed)
    args += ["--pid"]        # separate PID namespace
    args += ["--mount"]      # separate mount namespace
    args += ["--fork"]       # needed for --pid
    if cfg.network_isolated:
        args += ["--net"]    # separate network namespace (no internet)
    args += ["--map-root-user"]  # map current user to root inside
    return args


def run_in_unshare(cfg: LabConfig, cmd: str, capture_output: bool = False) -> tuple[int, str]:
    prefix = _unshare_prefix(cfg)
    full_cmd = prefix + ["sh", "-c", cmd]

    env = {**os.environ, **(cfg.env_vars or {})}
    if capture_output:
        try:
            r = subprocess.run(full_cmd, capture_output=True, text=True, env=env, timeout=300)
            out = (r.stdout + r.stderr).strip()
            for line in out.splitlines():
                console.print(f"[dim]{line}[/dim]")
            return r.returncode, out
        except subprocess.TimeoutExpired:
            return -1, "(timed out)"
    else:
        result = subprocess.run(full_cmd, env=env)
        return result.returncode, ""


def shell_in_unshare(cfg: LabConfig) -> int:
    prefix = _unshare_prefix(cfg)
    console.print(f"[bold cyan]Dropping into unshare shell [{cfg.name}][/bold cyan]")
    console.print(f"[dim]Network isolated: {cfg.network_isolated}  PID/mount namespace: yes[/dim]")
    console.print(f"[dim]Type 'exit' to leave the lab.[/dim]\n")
    result = subprocess.run(prefix + [os.environ.get("SHELL", "/bin/bash")])
    return result.returncode


# ── firejail ──────────────────────────────────────────────────────────────────

def _firejail_prefix(cfg: LabConfig) -> list[str]:
    args = ["firejail"]
    args += ["--quiet"]
    args += ["--private"]           # private /home, /tmp
    args += ["--private-dev"]       # private /dev
    args += ["--nogroups"]
    args += ["--nonewprivs"]
    args += ["--seccomp"]           # seccomp filter

    if cfg.network_isolated:
        args += ["--net=none"]

    for m in cfg.readonly_mounts:
        host, _, cont = m.partition(":")
        cont = cont or host
        args += [f"--bind-try={host},{cont}"]

    for k, v in (cfg.env_vars or {}).items():
        args += [f"--env={k}={v}"]

    return args


def run_in_firejail(cfg: LabConfig, cmd: str, capture_output: bool = False) -> tuple[int, str]:
    prefix = _firejail_prefix(cfg)
    full_cmd = prefix + ["sh", "-c", cmd]

    if capture_output:
        try:
            r = subprocess.run(full_cmd, capture_output=True, text=True, timeout=300)
            out = (r.stdout + r.stderr).strip()
            for line in out.splitlines():
                console.print(f"[dim]{line}[/dim]")
            return r.returncode, out
        except subprocess.TimeoutExpired:
            return -1, "(timed out)"
    else:
        result = subprocess.run(full_cmd)
        return result.returncode, ""


def shell_in_firejail(cfg: LabConfig) -> int:
    prefix = _firejail_prefix(cfg)
    console.print(f"[bold cyan]Dropping into firejail shell [{cfg.name}][/bold cyan]")
    console.print(f"[dim]seccomp + private home/dev  Network: {'none' if cfg.network_isolated else 'shared'}[/dim]")
    console.print(f"[dim]Type 'exit' to leave the lab.[/dim]\n")
    result = subprocess.run(prefix + [os.environ.get("SHELL", "/bin/bash")])
    return result.returncode


# ── systemd-nspawn ────────────────────────────────────────────────────────────

def _ensure_nspawn_root(cfg: LabConfig) -> Path:
    """Return (and create if needed) the chroot directory for this lab."""
    root = Path(cfg.nspawn_root) if cfg.nspawn_root else (
        Path.home() / ".rudra" / "lab" / "labs" / cfg.name / "rootfs"
    )
    if not root.exists():
        console.print(f"[dim]Creating minimal nspawn rootfs at {root}...[/dim]")
        root.mkdir(parents=True)
        # Bootstrap a minimal Debian rootfs if debootstrap is available
        if shutil.which("debootstrap"):
            r = subprocess.run(
                ["sudo", "debootstrap", "--variant=minbase", "stable", str(root)],
                timeout=300,
            )
            if r.returncode != 0:
                console.print("[yellow]debootstrap failed — nspawn will use your system root (less isolated).[/yellow]")
        else:
            console.print("[yellow]debootstrap not found — nspawn rootfs will be minimal.[/yellow]")
            # Create a bare-minimum structure so nspawn won't refuse to start
            for d in ("bin", "etc", "proc", "sys", "dev", "tmp", "usr"):
                (root / d).mkdir(exist_ok=True)
    return root


def _nspawn_prefix(cfg: LabConfig) -> list[str]:
    root = _ensure_nspawn_root(cfg)
    args = ["sudo", "systemd-nspawn"]
    args += [f"--directory={root}"]
    args += ["--private-users=pick"]
    args += ["--private-network"] if cfg.network_isolated else []
    args += ["--read-only"] if not cfg.writable_mounts else []

    for m in cfg.readonly_mounts:
        args += [f"--bind-ro={m}"]
    for m in cfg.writable_mounts:
        args += [f"--bind={m}"]

    return args


def run_in_nspawn(cfg: LabConfig, cmd: str, capture_output: bool = False) -> tuple[int, str]:
    prefix = _nspawn_prefix(cfg)
    full_cmd = prefix + ["/bin/sh", "-c", cmd]

    env = {k: v for k, v in (cfg.env_vars or {}).items()}
    if capture_output:
        try:
            r = subprocess.run(full_cmd, capture_output=True, text=True,
                               env={**os.environ, **env}, timeout=300)
            out = (r.stdout + r.stderr).strip()
            for line in out.splitlines():
                console.print(f"[dim]{line}[/dim]")
            return r.returncode, out
        except subprocess.TimeoutExpired:
            return -1, "(timed out)"
    else:
        result = subprocess.run(full_cmd, env={**os.environ, **env})
        return result.returncode, ""


def shell_in_nspawn(cfg: LabConfig) -> int:
    prefix = _nspawn_prefix(cfg)
    console.print(f"[bold cyan]Dropping into nspawn shell [{cfg.name}][/bold cyan]")
    console.print(f"[dim]Network isolated: {cfg.network_isolated}[/dim]")
    console.print(f"[dim]Type 'exit' to leave the lab.[/dim]\n")
    result = subprocess.run(prefix + ["/bin/bash"])
    return result.returncode


# ── env-only (weakest, always available) ─────────────────────────────────────

def run_in_env(cfg: LabConfig, cmd: str,
               venv_path: Optional[Path] = None,
               capture_output: bool = False) -> tuple[int, str]:
    """Run in an isolated env — just env vars + optional venv, no namespace."""
    env = {**os.environ}

    # Strip dangerous env vars
    for dangerous in ("LD_PRELOAD", "LD_LIBRARY_PATH", "PYTHONPATH"):
        env.pop(dangerous, None)

    env.update(cfg.env_vars or {})

    if venv_path and venv_path.exists():
        env["VIRTUAL_ENV"] = str(venv_path)
        env["PATH"] = f"{venv_path/'bin'}:{env.get('PATH','')}"

    if capture_output:
        try:
            r = subprocess.run(
                ["sh", "-c", cmd],
                capture_output=True, text=True, env=env, timeout=300,
            )
            out = (r.stdout + r.stderr).strip()
            for line in out.splitlines():
                console.print(f"[dim]{line}[/dim]")
            return r.returncode, out
        except subprocess.TimeoutExpired:
            return -1, "(timed out)"
    else:
        result = subprocess.run(["sh", "-c", cmd], env=env)
        return result.returncode, ""
