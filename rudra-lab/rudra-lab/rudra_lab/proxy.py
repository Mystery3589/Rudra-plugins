"""Per-lab network proxy — spins up for the run, dies when done.

Supports two backends (auto-picked):
  mitmproxy  — full HTTPS inspection, request logging, scriptable hooks
  tinyproxy  — lightweight, allowlist/denylist, no HTTPS inspection

Internet modes:
  no-internet  — network namespace fully isolated, no proxy needed
  capture      — proxy up, everything allowed, all requests logged
  denylist     — block known-bad domains (Steven Black), log rest
  allowlist    — only explicitly listed domains pass
"""

from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from rich.console import Console

console = Console()

_LAB_DIR_REF = Path.home() / ".rudra" / "lab"
BLOCKLIST_URL = "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts"
BLOCKLIST_PATH = _LAB_DIR_REF / "blocklist.hosts"
BLOCKLIST_MAX_AGE = 86400 * 3


@dataclass
class ProxyConfig:
    mode: str            = "no-internet"
    port: int            = 0
    backend: str         = ""
    allowlist: list      = field(default_factory=list)
    denylist_extra: list = field(default_factory=list)
    log_path: Path       = field(default_factory=lambda: _LAB_DIR_REF / "proxy.log")
    pid: int             = 0


@dataclass
class ProxySession:
    cfg: ProxyConfig
    proc: Optional[subprocess.Popen] = None
    tmpdir: Optional[str] = None
    env_vars: dict = field(default_factory=dict)


def _fetch_blocklist() -> set:
    if (BLOCKLIST_PATH.exists() and
            time.time() - BLOCKLIST_PATH.stat().st_mtime < BLOCKLIST_MAX_AGE):
        console.print("[dim]Using cached blocklist.[/dim]")
    else:
        console.print("[dim]Fetching Steven Black blocklist...[/dim]")
        try:
            with urllib.request.urlopen(BLOCKLIST_URL, timeout=15) as r:
                BLOCKLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
                BLOCKLIST_PATH.write_bytes(r.read())
            console.print("[dim]Blocklist updated.[/dim]")
        except Exception as e:
            console.print(f"[yellow]Could not fetch blocklist: {e}[/yellow]")
            if not BLOCKLIST_PATH.exists():
                return set()

    blocked: set = set()
    for line in BLOCKLIST_PATH.read_text(errors="replace").splitlines():
        line = line.strip()
        if line.startswith("#") or not line:
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[0] in ("0.0.0.0", "127.0.0.1"):
            blocked.add(parts[1].lower())
    return blocked


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


_MITM_ADDON = '''\
import json, time
from mitmproxy import http

ALLOWLIST = {allowlist!r}
BLOCKLIST = {blocklist!r}
MODE      = {mode!r}
LOG_PATH  = {log_path!r}

def _log(flow, blocked=False, reason=""):
    entry = dict(time=time.time(), method=flow.request.method,
                 url=flow.request.pretty_url, host=flow.request.pretty_host,
                 blocked=blocked, reason=reason)
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\\n")

def request(flow: http.HTTPFlow):
    host = flow.request.pretty_host.lower()
    if MODE == "allowlist":
        if not any(host == a or host.endswith("." + a) for a in ALLOWLIST):
            _log(flow, blocked=True, reason="not in allowlist")
            flow.response = http.Response.make(403, f"rudra-lab: {{host}} blocked", {{"Content-Type":"text/plain"}})
            return
    elif MODE == "denylist":
        if host in BLOCKLIST or any(host.endswith("." + b) for b in BLOCKLIST):
            _log(flow, blocked=True, reason="in denylist")
            flow.response = http.Response.make(403, f"rudra-lab: {{host}} blocked", {{"Content-Type":"text/plain"}})
            return
    _log(flow, blocked=False)
'''


def _start_mitmproxy(cfg: ProxyConfig, tmpdir: str, blocklist: set) -> Optional[subprocess.Popen]:
    script = Path(tmpdir) / "addon.py"
    script.write_text(_MITM_ADDON.format(
        allowlist = cfg.allowlist,
        blocklist = list(blocklist)[:5000],
        mode      = cfg.mode,
        log_path  = str(cfg.log_path),
    ))
    bin_ = _find_mitmdump()
    if not bin_:
        console.print("[red]mitmdump not found — cannot start proxy.[/red]")
        return None
    cmd = [bin_, "--listen-host", "127.0.0.1",
           "--listen-port", str(cfg.port), "--quiet", "-s", str(script)]
    if cfg.mode == "capture":
        cmd += ["--save-stream-file", str(Path(tmpdir) / "flows.mitm")]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        time.sleep(1.2)
        if proc.poll() is not None:
            stderr = proc.stderr.read() if proc.stderr else ""
            console.print(f"[red]mitmdump failed to start:[/red]")
            if stderr.strip():
                console.print(f"[dim]{stderr.strip()}[/dim]")
            return None
        return proc
    except FileNotFoundError:
        return None


_TINY_CONF = """\
Port {port}
Listen 127.0.0.1
Timeout 30
LogLevel Notice
LogFile "{log_path}"
MaxClients 32
{filter_lines}
"""


def _start_tinyproxy(cfg: ProxyConfig, tmpdir: str, blocklist: set) -> Optional[subprocess.Popen]:
    filter_lines = []
    fpath = Path(tmpdir) / "filter.txt"
    if cfg.mode == "allowlist":
        fpath.write_text("\n".join(cfg.allowlist) + "\n")
        filter_lines = [f'Filter "{fpath}"', "FilterDefaultDeny Yes"]
    elif cfg.mode == "denylist":
        combined = list(blocklist)[:10000] + cfg.denylist_extra
        fpath.write_text("\n".join(combined) + "\n")
        filter_lines = [f'Filter "{fpath}"', "FilterDefaultDeny No"]
    conf = Path(tmpdir) / "tinyproxy.conf"
    conf.write_text(_TINY_CONF.format(
        port=cfg.port, log_path=str(cfg.log_path),
        filter_lines="\n".join(filter_lines),
    ))
    try:
        proc = subprocess.Popen(["tinyproxy", "-d", "-c", str(conf)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        time.sleep(0.8)
        if proc.poll() is not None:
            return None
        return proc
    except FileNotFoundError:
        return None


def _find_mitmdump() -> Optional[str]:
    """Find mitmdump using every reasonable strategy."""
    import sys
    import sysconfig

    # 0. Ensure /usr/sbin and other standard dirs are on PATH before searching.
    #    The plugin's __init__.py does this at import time but proxy.py may be
    #    imported before __init__.py's _ensure_path() runs.
    for d in ("/usr/sbin", "/usr/bin", "/usr/local/bin", "/usr/local/sbin"):
        if d not in os.environ.get("PATH", ""):
            os.environ["PATH"] = d + ":" + os.environ.get("PATH", "")

    # 1. Normal PATH (works if rudra's venv has it)
    p = shutil.which("mitmdump")
    if p:
        return p

    # 2. Ask the user's shell — bypasses venv PATH stripping
    try:
        r = subprocess.run(
            ["sh", "-c", "which mitmdump 2>/dev/null || command -v mitmdump 2>/dev/null"],
            capture_output=True, text=True, timeout=3,
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except Exception:
        pass

    # 3. The scripts dir of the Python interpreter running rudra
    try:
        candidate = Path(sysconfig.get_path("scripts")) / "mitmdump"
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    except Exception:
        pass

    # 4. sys.prefix/bin — covers venvs and conda envs
    try:
        candidate = Path(sys.prefix) / "bin" / "mitmdump"
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    except Exception:
        pass

    # 5. Hard-coded common locations
    for candidate in (
        Path("/usr/bin/mitmdump"),
        Path("/usr/local/bin/mitmdump"),
        Path("/usr/lib/mitmproxy/bin/mitmdump"),
        Path.home() / ".local" / "bin" / "mitmdump",
        Path.home() / ".local" / "pipx" / "venvs" / "mitmproxy" / "bin" / "mitmdump",
    ):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)

    return None


def detect_proxy_backend() -> str:
    if _find_mitmdump():
        return "mitmproxy"
    if shutil.which("tinyproxy"):
        return "tinyproxy"
    return "none"


def start_proxy(cfg: ProxyConfig) -> Optional[ProxySession]:
    if cfg.mode == "no-internet":
        return None
    backend = cfg.backend if (cfg.backend and cfg.backend != "none") else detect_proxy_backend()
    if backend == "none":
        console.print("[yellow]No proxy backend found.[/yellow]")
        console.print("[dim]mitmdump (mitmproxy) is required for lab network filtering/logging.[/dim]")
        installed = False
        try:
            if typer.confirm("Would you like to install mitmproxy now?", default=True):
                console.print("[bold cyan]==> Installing mitmproxy...[/bold cyan]")
                if shutil.which("pipx"):
                    subprocess.run(["pipx", "install", "mitmproxy"])
                elif shutil.which("pip3"):
                    subprocess.run(["pip3", "install", "--user", "mitmproxy"])
                elif shutil.which("pip"):
                    subprocess.run(["pip", "install", "--user", "mitmproxy"])
                backend = detect_proxy_backend()
                if backend != "none":
                    installed = True
                    console.print("[bold green]✓ mitmproxy installed successfully.[/bold green]")
        except Exception:
            pass

        if not installed and backend == "none":
            console.print("[dim]mitmdump (part of mitmproxy) is required. Install it with:[/dim]")
            console.print("[dim]  pipx install mitmproxy   OR   pip install --user mitmproxy[/dim]")
            console.print("[yellow]Falling back to no-internet.[/yellow]")
            return None

    cfg.port    = _free_port()
    cfg.backend = backend

    blocklist: set = set()
    if cfg.mode == "denylist":
        blocklist = _fetch_blocklist()
        blocklist.update(cfg.denylist_extra)

    tmpdir = tempfile.mkdtemp(prefix="rudra-lab-proxy-")
    proc = (_start_mitmproxy if backend == "mitmproxy" else _start_tinyproxy)(cfg, tmpdir, blocklist)

    if proc is None:
        console.print(f"[red]Proxy backend '{backend}' failed to start.[/red]")
        return None

    cfg.pid = proc.pid
    proxy_url = f"http://127.0.0.1:{cfg.port}"
    console.print(f"[bold green]✓ Proxy up[/bold green]  [dim]{backend} @ 127.0.0.1:{cfg.port}  mode={cfg.mode}[/dim]")

    return ProxySession(
        cfg=cfg, proc=proc, tmpdir=tmpdir,
        env_vars={
            "http_proxy": proxy_url, "https_proxy": proxy_url,
            "HTTP_PROXY": proxy_url, "HTTPS_PROXY": proxy_url,
            "NO_PROXY": "localhost,127.0.0.1",
        },
    )


def stop_proxy(session: Optional[ProxySession]) -> list:
    if session is None:
        return []
    if session.proc and session.proc.poll() is None:
        session.proc.terminate()
        try:
            session.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            session.proc.kill()

    requests = []
    if session.cfg.log_path.exists():
        for line in session.cfg.log_path.read_text().splitlines():
            try:
                requests.append(json.loads(line.strip()))
            except Exception:
                pass

    if session.tmpdir:
        import shutil as _sh
        _sh.rmtree(session.tmpdir, ignore_errors=True)
    return requests


def summarise_requests(requests: list) -> dict:
    total   = len(requests)
    blocked = [r for r in requests if r.get("blocked")]
    allowed = [r for r in requests if not r.get("blocked")]
    hosts: dict = {}
    for r in requests:
        h = r.get("host", "?")
        hosts[h] = hosts.get(h, 0) + 1
    return {
        "total":         total,
        "blocked_count": len(blocked),
        "allowed_count": len(allowed),
        "unique_hosts":  len(hosts),
        "top_hosts":     sorted(hosts.items(), key=lambda x: -x[1])[:10],
        "blocked_hosts": list({r.get("host") for r in blocked}),
        "all_requests":  requests,
    }
