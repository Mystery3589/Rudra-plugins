"""Non-Docker isolation backends: unshare, firejail, systemd-nspawn."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from rich.console import Console

from rudra_lab.helpers import LabConfig, capture

console = Console()


# ── unshare ───────────────────────────────────────────────────────────────────

def _unshare_prefix(cfg: LabConfig) -> list[str]:
    args = ["unshare", "--user", "--pid", "--mount", "--fork", "--map-root-user"]
    if cfg.network_isolated:
        args += ["--net"]
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
    args = ["firejail", "--quiet", "--private", "--private-dev",
            "--nogroups", "--nonewprivs", "--seccomp"]
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
    root = Path(cfg.nspawn_root) if cfg.nspawn_root else (
        Path.home() / ".rudra" / "lab" / "labs" / cfg.name / "rootfs"
    )
    if not root.exists():
        console.print(f"[dim]Creating minimal nspawn rootfs at {root}...[/dim]")
        root.mkdir(parents=True)
        if shutil.which("debootstrap"):
            r = subprocess.run(
                ["sudo", "debootstrap", "--variant=minbase", "stable", str(root)],
                timeout=300,
            )
            if r.returncode != 0:
                console.print("[yellow]debootstrap failed — falling back to minimal rootfs.[/yellow]")
        if not shutil.which("debootstrap") or True:
            console.print("[yellow]debootstrap not found — nspawn rootfs will be minimal.[/yellow]")
            for d in ("bin", "etc", "proc", "sys", "dev", "tmp", "usr", "lab"):
                (root / d).mkdir(exist_ok=True)
    return root


def _prepare_nspawn_src(cfg: LabConfig) -> Optional[Path]:
    """
    Copy the source directory into the lab's own scratch space and return
    the scratch copy path.  The container gets this copy as a plain writable
    --bind, so nspawn never has to fight with readonly mounts or staging dirs.

    The copy lives at:
      ~/.rudra/lab/labs/<name>/src_copy/

    On subsequent runs we rsync (or re-copy) only changed files so it stays
    fast.  Returns None if cfg has no source path.
    """
    if not cfg.source_path:
        return None

    src = Path(cfg.source_path)
    if not src.is_dir():
        return None

    lab_base = Path.home() / ".rudra" / "lab" / "labs" / cfg.name
    dst = lab_base / "src_copy"

    if dst.exists():
        # Fast update: rsync if available, else full re-copy
        if shutil.which("rsync"):
            subprocess.run(
                ["rsync", "-a", "--delete", f"{src}/", f"{dst}/"],
                capture_output=True,
            )
        else:
            shutil.rmtree(dst)
            shutil.copytree(src, dst, symlinks=True)
    else:
        console.print(f"[dim]Copying source into lab scratch...[/dim]")
        shutil.copytree(src, dst, symlinks=True)

    # Make the scratch copy world-writable so that nspawn's user namespace
    # UID remapping doesn't block writes.  Inside the container the process
    # runs as a remapped UID that doesn't match the host owner, so without
    # this every write (e.g. expo writing .expo/dev/logs/) gets EACCES.
    subprocess.run(["chmod", "-R", "a+rwX", str(dst)], capture_output=True)

    return dst


def _nspawn_prefix(cfg: LabConfig, src_copy: Optional[Path]) -> list[str]:
    root = _ensure_nspawn_root(cfg)

    args = ["sudo", "systemd-nspawn"]
    args += [f"--directory={root}"]
    args += ["--private-users=pick"]
    args += ["--private-network"] if cfg.network_isolated else []

    # Bind host system tools read-only for minimal rootfs
    bin_in_root = root / "bin"
    if bin_in_root.exists() and not any(bin_in_root.iterdir()):
        for d in ("/bin", "/usr", "/lib", "/sbin", "/lib64"):
            if Path(d).exists():
                args += [f"--bind-ro={d}"]

    # Mount the writable scratch copy at /lab/src.
    # This is a plain --bind of a normal host directory — no readonly mounts,
    # no overlayfs, no staging mkdir conflicts. nspawn just binds the dir.
    if src_copy:
        mp = root / "lab" / "src"
        mp.mkdir(parents=True, exist_ok=True)
        args += [f"--bind={src_copy}:/lab/src"]
        args += ["--chdir=/lab/src"]

    # Any extra writable mounts
    for m in cfg.writable_mounts:
        host, _, cont = m.partition(":")
        cont = cont or host
        (root / cont.lstrip("/")).mkdir(parents=True, exist_ok=True)
        args += [f"--bind={m}"]

    # Inject env vars
    for k, v in (cfg.env_vars or {}).items():
        args += [f"--setenv={k}={v}"]

    return args


def run_in_nspawn(cfg: LabConfig, cmd: str, capture_output: bool = False) -> tuple[int, str]:
    src_copy = _prepare_nspawn_src(cfg)
    prefix = _nspawn_prefix(cfg, src_copy)
    full_cmd = prefix + ["/bin/sh", "-c", cmd]
    timeout = getattr(cfg, "timeout", None) or None  # None = no timeout

    if capture_output:
        # Stream output to terminal in real time AND collect it for the log.
        import threading
        lines: list[str] = []

        proc = subprocess.Popen(
            full_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        def _stream():
            for line in proc.stdout:
                print(line, end="", flush=True)
                lines.append(line)

        t = threading.Thread(target=_stream, daemon=True)
        t.start()
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            t.join(timeout=2)
            return -1, "".join(lines)
        t.join(timeout=2)
        return proc.returncode, "".join(lines)
    else:
        try:
            result = subprocess.run(full_cmd, timeout=timeout)
            return result.returncode, ""
        except subprocess.TimeoutExpired:
            return -1, "(timed out)"


def shell_in_nspawn(cfg: LabConfig) -> int:
    src_copy = _prepare_nspawn_src(cfg)
    prefix = _nspawn_prefix(cfg, src_copy)
    console.print(f"[bold cyan]Dropping into nspawn shell [{cfg.name}][/bold cyan]")
    console.print(f"[dim]Network isolated: {cfg.network_isolated}[/dim]")
    console.print(f"[dim]Type 'exit' to leave the lab.[/dim]\n")
    result = subprocess.run(prefix + ["/bin/bash"])
    return result.returncode


# ── env-only (weakest, always available) ─────────────────────────────────────

def run_in_env(cfg: LabConfig, cmd: str,
               venv_path: Optional[Path] = None,
               capture_output: bool = False) -> tuple[int, str]:
    env = {**os.environ}
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
