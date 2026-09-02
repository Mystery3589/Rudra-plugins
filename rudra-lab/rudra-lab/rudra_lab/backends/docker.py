"""Docker isolation backend for rudra-lab."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Optional

from rich.console import Console

from rudra_lab.helpers import LabConfig, capture, run_capture

console = Console()

_DEFAULT_SECURITY_OPTS = [
    "--security-opt=no-new-privileges",
    "--cap-drop=ALL",
    "--read-only",
]


def _base_run_args(cfg: LabConfig, interactive: bool = False) -> list[str]:
    args = ["docker", "run", "--rm"]

    if interactive:
        args += ["-it"]

    # Network isolation
    if cfg.network_isolated:
        args += ["--network=none"]

    # Security hardening
    args += _DEFAULT_SECURITY_OPTS

    # Writable tmpfs so --read-only doesn't break everything
    args += ["--tmpfs=/tmp:rw,noexec,nosuid,size=256m"]
    args += ["--tmpfs=/run:rw,noexec,nosuid,size=64m"]

    # Name
    args += [f"--name=rudra-lab-{cfg.name}"]

    # Mounts
    for m in cfg.readonly_mounts:
        parts = m.split(":")
        host, cont = parts[0], (parts[1] if len(parts) > 1 else parts[0])
        args += [f"--mount=type=bind,source={host},target={cont},readonly"]

    for m in cfg.writable_mounts:
        parts = m.split(":")
        host, cont = parts[0], (parts[1] if len(parts) > 1 else parts[0])
        args += [f"--mount=type=bind,source={host},target={cont}"]

    # Port bindings (only if network not fully isolated)
    if not cfg.network_isolated:
        for p in cfg.port_bindings:
            args += [f"-p={p}"]

    # Env vars
    for k, v in cfg.env_vars.items():
        args += [f"-e={k}={v}"]

    # Memory + CPU limits for safety
    args += ["--memory=512m", "--cpus=1.0", "--pids-limit=256"]

    return args


def pull_image(image: str) -> bool:
    console.print(f"[dim]Pulling {image}...[/dim]")
    code, out = capture(["docker", "pull", image], timeout=120)
    if code != 0:
        console.print(f"[red]Failed to pull {image}:[/red]\n{out}")
        return False
    return True


def build_image(cfg: LabConfig, dockerfile_content: str) -> Optional[str]:
    """Build a custom image from a Dockerfile string. Returns image tag or None."""
    import tempfile, os
    tag = f"rudra-lab-{cfg.name}:latest"
    with tempfile.TemporaryDirectory() as tmpdir:
        df = Path(tmpdir) / "Dockerfile"
        df.write_text(dockerfile_content)
        code, out = capture(["docker", "build", "-t", tag, tmpdir], timeout=300)
        if code != 0:
            console.print(f"[red]Image build failed:[/red]\n{out}")
            return None
    return tag


def run_in_docker(cfg: LabConfig, cmd: str, capture_output: bool = False) -> tuple[int, str]:
    args = _base_run_args(cfg)
    args.append(cfg.docker_image)
    args += ["sh", "-c", cmd]

    if capture_output:
        return run_capture(args, f"Running in Docker [{cfg.name}]")
    else:
        import subprocess, os
        result = subprocess.run(args, env={**os.environ})
        return result.returncode, ""


def shell_in_docker(cfg: LabConfig, shell: str = "/bin/bash") -> int:
    args = _base_run_args(cfg, interactive=True)
    args.append(cfg.docker_image)
    args.append(shell)

    console.print(f"[bold cyan]Dropping into Docker shell [{cfg.name}][/bold cyan]")
    console.print(f"[dim]Image: {cfg.docker_image}  Network: {'none' if cfg.network_isolated else 'bridge'}[/dim]")
    console.print(f"[dim]Type 'exit' to leave the lab.[/dim]\n")

    import subprocess, os
    result = subprocess.run(args, env={**os.environ})
    return result.returncode


def snapshot_container(cfg: LabConfig, tag: Optional[str] = None) -> Optional[str]:
    """Commit the current container state as an image snapshot."""
    if not cfg.docker_id:
        console.print("[yellow]No running container to snapshot.[/yellow]")
        return None
    snap_tag = tag or f"rudra-lab-{cfg.name}-snap:{__import__('time').strftime('%Y%m%d%H%M%S')}"
    code, out = capture(["docker", "commit", cfg.docker_id, snap_tag])
    if code != 0:
        console.print(f"[red]Snapshot failed:[/red] {out}")
        return None
    return snap_tag


def stop_container(name: str) -> None:
    capture(["docker", "stop", f"rudra-lab-{name}"], timeout=10)
    capture(["docker", "rm", "-f", f"rudra-lab-{name}"], timeout=10)


def container_running(name: str) -> bool:
    code, out = capture(["docker", "ps", "--filter", f"name=rudra-lab-{name}", "--format={{.Names}}"])
    return code == 0 and f"rudra-lab-{name}" in out


def list_lab_images() -> list[str]:
    code, out = capture(["docker", "images", "--filter=reference=rudra-lab-*", "--format={{.Repository}}:{{.Tag}}"])
    return out.splitlines() if code == 0 and out.strip() else []


def remove_lab_image(cfg: LabConfig) -> None:
    capture(["docker", "rmi", "-f", cfg.docker_image])
