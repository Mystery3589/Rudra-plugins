"""Dispatch run/shell calls to the right backend based on lab tier."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from rich.console import Console

from rudra_lab.helpers import LabConfig, Tier

console = Console()


def run_in_lab(cfg: LabConfig, cmd: str, capture_output: bool = False) -> tuple[int, str]:
    """Run a command in the lab using whatever tier is configured."""
    tier = Tier(cfg.tier)

    if tier == Tier.DOCKER:
        from rudra_lab.backends.docker import run_in_docker
        return run_in_docker(cfg, cmd, capture_output)

    elif tier == Tier.NSPAWN:
        from rudra_lab.backends.unshare import run_in_nspawn
        return run_in_nspawn(cfg, cmd, capture_output)

    elif tier == Tier.FIREJAIL:
        from rudra_lab.backends.unshare import run_in_firejail
        return run_in_firejail(cfg, cmd, capture_output)

    elif tier == Tier.UNSHARE:
        from rudra_lab.backends.unshare import run_in_unshare
        return run_in_unshare(cfg, cmd, capture_output)

    else:  # ENV
        venv = Path(cfg.nspawn_root) if cfg.nspawn_root else None
        from rudra_lab.backends.unshare import run_in_env
        return run_in_env(cfg, cmd, venv_path=venv, capture_output=capture_output)


def shell_in_lab(cfg: LabConfig) -> int:
    """Drop into an interactive shell in the lab."""
    tier = Tier(cfg.tier)

    if tier == Tier.DOCKER:
        from rudra_lab.backends.docker import shell_in_docker
        return shell_in_docker(cfg)

    elif tier == Tier.NSPAWN:
        from rudra_lab.backends.unshare import shell_in_nspawn
        return shell_in_nspawn(cfg)

    elif tier == Tier.FIREJAIL:
        from rudra_lab.backends.unshare import shell_in_firejail
        return shell_in_firejail(cfg)

    elif tier == Tier.UNSHARE:
        from rudra_lab.backends.unshare import shell_in_unshare
        return shell_in_unshare(cfg)

    else:
        console.print("[yellow]env tier has no true shell isolation — launching a subshell.[/yellow]")
        import subprocess, os
        env = {**os.environ, **(cfg.env_vars or {})}
        result = subprocess.run([os.environ.get("SHELL", "/bin/bash")], env=env)
        return result.returncode


def teardown_lab(cfg: LabConfig) -> None:
    """Tear down any running backend resources for a lab."""
    tier = Tier(cfg.tier)

    if tier == Tier.DOCKER:
        from rudra_lab.backends.docker import stop_container
        stop_container(cfg.name)

    elif tier == Tier.NSPAWN:
        # nspawn processes are killed on exit normally; nothing persistent to stop
        pass

    elif tier in (Tier.FIREJAIL, Tier.UNSHARE, Tier.ENV):
        pass  # stateless — processes die on their own
