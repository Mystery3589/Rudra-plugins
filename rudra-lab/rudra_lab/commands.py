"""rudra lab — all CLI commands."""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from rudra_lab.helpers import (
    LAB_DIR, LABS_DIR, LOGS_DIR,
    LabConfig, ProjectType, Tier,
    best_tier, capture, detect_project_type, detect_tiers,
    lab_dir, list_labs, load_lab, log_run, save_lab,
)

app = typer.Typer(no_args_is_help=True)
console = Console()

def _hint_exit_code(exit_code: int, tier: "Tier") -> None:
    """Print a human-readable diagnostic when a container exits non-zero."""
    if exit_code == 0:
        return
    if tier == Tier.NSPAWN and exit_code == 7:
        console.print(
            "[yellow]Hint: nspawn exit 7 usually means a permission error inside the "
            "container (e.g. a tool tried to write into the read-only source mount). "
            "Check for EACCES in the output above. rudra-lab's bootstrap should have "
            "added writable scratch mounts automatically — if one is missing, file an "
            "issue or add it to setup_node / the relevant setup_* function in "
            "env_setup.py.[/yellow]"
        )
    elif exit_code == 1:
        console.print("[dim]Hint: exit 1 is a generic failure — check the output above for details.[/dim]")


TIER_COLORS = {
    "docker":   "green",
    "nspawn":   "cyan",
    "firejail": "blue",
    "unshare":  "yellow",
    "env":      "dim",
}

STATUS_COLORS = {
    "created":   "dim",
    "running":   "green",
    "stopped":   "yellow",
    "destroyed": "red",
}


# ── create ────────────────────────────────────────────────────────────────────

@app.command()
def create(
    name: Annotated[str, typer.Argument(help="Lab name.")],
    tier: Annotated[Optional[str], typer.Option("--tier", "-t",
        help="Isolation tier: docker, nspawn, firejail, unshare, env. Auto-selects best if omitted.")] = None,
    source: Annotated[Optional[str], typer.Option("--source", "-s",
        help="Source directory to mount into the lab.")] = None,
    image: Annotated[str, typer.Option("--image",
        help="Docker image (only for docker tier).")] = "ubuntu:22.04",
    no_network: Annotated[bool, typer.Option("--no-network",
        help="Fully isolate network (default: True).")] = True,
    disposable: Annotated[bool, typer.Option("--disposable/--persistent",
        help="Auto-destroy after run (default: True).")] = True,
    env: Annotated[Optional[list[str]], typer.Option("--env", "-e",
        help="Extra env vars as KEY=VALUE.")] = None,
    port: Annotated[Optional[list[str]], typer.Option("--port", "-p",
        help="Port bindings as host:container.")] = None,
):
    """Create a named lab environment.

    Examples:
      rudra lab create mylab
      rudra lab create mylab --tier docker --source ./project
      rudra lab create mylab --tier firejail --no-network
      rudra lab create testenv --image python:3.12 --source .
      rudra lab create netlab --no-network=false --port 8080:80
    """
    if (LABS_DIR / name).exists():
        console.print(f"[yellow]Lab '{name}' already exists.[/yellow]")
        if not typer.confirm("Recreate it?", default=False):
            raise typer.Exit(0)
        _destroy_lab_data(name)

    chosen_tier = best_tier(tier)
    available   = detect_tiers()

    # Show tier selection
    console.print(f"\n[bold]Available isolation tiers:[/bold]")
    for t in detect_tiers():
        marker = "[bold green]✓ selected[/bold green]" if t == chosen_tier else "[dim]available[/dim]"
        safety = "█" * Tier.__members__[t.name].__class__
        from rudra_lab.helpers import TIER_SAFETY, TIER_DESCRIPTIONS
        safety_bar = "[green]" + "█" * TIER_SAFETY[t] + "[/green]" + "[dim]" + "░" * (5 - TIER_SAFETY[t]) + "[/dim]"
        console.print(f"  {safety_bar}  [bold]{t.value:<10}[/bold]  {marker}  [dim]{TIER_DESCRIPTIONS[t]}[/dim]")

    # Auto-detect project type
    src_path = Path(source).resolve() if source else None
    ptype = detect_project_type(src_path) if src_path else ProjectType.UNKNOWN
    if ptype != ProjectType.UNKNOWN:
        console.print(f"\n[dim]Detected project type: [bold]{ptype.value}[/bold][/dim]")

    # Parse env vars
    env_dict: dict[str, str] = {}
    for e in (env or []):
        if "=" in e:
            k, _, v = e.partition("=")
            env_dict[k.strip()] = v.strip()

    cfg = LabConfig(
        name             = name,
        tier             = chosen_tier.value,
        project_type     = ptype.value,
        source_path      = str(src_path) if src_path else "",
        disposable       = disposable,
        network_isolated = no_network,
        docker_image     = image,
        env_vars         = env_dict,
        port_bindings    = port or [],
        readonly_mounts  = [f"{src_path}:/lab/src"] if src_path else [],
        status           = "created",
    )

    # Docker: pull image
    if chosen_tier == Tier.DOCKER:
        from rudra_lab.backends.docker import pull_image
        if not pull_image(image):
            console.print("[yellow]Image pull failed — lab created anyway, will retry on first run.[/yellow]")

    save_lab(cfg)

    console.print(f"\n[bold green]✓ Lab '{name}' created.[/bold green]")
    console.print(f"  Tier       : [bold]{chosen_tier.value}[/bold]")
    console.print(f"  Network    : {'isolated' if no_network else 'shared'}")
    console.print(f"  Disposable : {disposable}")
    if src_path:
        console.print(f"  Source     : {src_path}  [dim]({ptype.value})[/dim]")
    console.print()
    console.print(f"[dim]Run:   rudra lab run {name} <command>[/dim]")
    console.print(f"[dim]Shell: rudra lab shell {name}[/dim]")


# ── run ───────────────────────────────────────────────────────────────────────

@app.command()
def run(
    name: Annotated[str, typer.Argument(help="Lab name.")],
    command: Annotated[str, typer.Argument(help="Command to run inside the lab.")],
    snapshot: Annotated[bool, typer.Option("--snapshot", "-S",
        help="Take before/after snapshots.")] = False,
    capture_: Annotated[bool, typer.Option("--capture", "-c",
        help="Capture and log output.")] = True,
    destroy_after: Annotated[Optional[bool], typer.Option("--destroy/--keep",
        help="Override disposable setting.")] = None,
    bootstrap: Annotated[bool, typer.Option("--bootstrap/--no-bootstrap",
        help="Auto-setup language env (venv/npm/cargo) before running.")] = True,
    timeout: Annotated[int, typer.Option("--timeout",
        help="Timeout in seconds.")] = 300,
):
    """Run a command inside a lab environment.

    Examples:
      rudra lab run mylab "python script.py"
      rudra lab run mylab "npm test" --snapshot
      rudra lab run mylab "bash install.sh" --capture
      rudra lab run suspicious "python main.py" --snapshot --destroy
    """
    cfg = load_lab(name)
    cfg.status = "running"
    cfg.last_run = datetime.now().isoformat()
    cfg.run_count += 1
    save_lab(cfg)

    console.print(f"\n[bold cyan]Lab:[/bold cyan] {name}  "
                  f"[bold cyan]Tier:[/bold cyan] {cfg.tier}  "
                  f"[bold cyan]Network:[/bold cyan] {'isolated' if cfg.network_isolated else 'shared'}")
    console.print(f"[bold cyan]CMD:[/bold cyan] {command}\n")

    # Bootstrap language env
    extra_env: dict[str, str] = {}
    if bootstrap and cfg.source_path:
        from rudra_lab.env_setup import bootstrap_env
        extra_env = bootstrap_env(cfg)
        if extra_env:
            cfg.env_vars = {**cfg.env_vars, **extra_env}

    # Snapshot before
    if snapshot:
        from rudra_lab.snapshot import take_snapshot
        watch = [cfg.source_path] if cfg.source_path else []
        take_snapshot(cfg, "before", paths=watch)

    # Run
    from rudra_lab.backends.dispatch import run_in_lab
    exit_code, output = run_in_lab(cfg, command, capture_output=capture_)

    # Snapshot after
    if snapshot:
        from rudra_lab.snapshot import take_snapshot, diff_snapshots
        watch = [cfg.source_path] if cfg.source_path else []
        take_snapshot(cfg, "after", paths=watch)
        diff_snapshots(cfg, "before", "after")

    # Log run
    if capture_:
        log_file = log_run(name, command, output, exit_code)
        console.print(f"\n[dim]Log saved: {log_file}[/dim]")

    # Status
    cfg.status = "stopped"
    save_lab(cfg)

    if exit_code == 0:
        console.print(f"\n[bold green]✓ Exited 0.[/bold green]")
    else:
        console.print(f"\n[bold red]✗ Exited {exit_code}.[/bold red]")
        _hint_exit_code(exit_code, Tier(cfg.tier))

    # Destroy if disposable
    should_destroy = destroy_after if destroy_after is not None else cfg.disposable
    if should_destroy:
        console.print(f"[dim]Disposable lab — cleaning up...[/dim]")
        _destroy_lab_data(name)
        console.print(f"[green]✓ Lab '{name}' destroyed.[/green]")

    raise typer.Exit(exit_code)


# ── shell ─────────────────────────────────────────────────────────────────────

@app.command()
def shell(
    name: Annotated[str, typer.Argument(help="Lab name.")],
    bootstrap: Annotated[bool, typer.Option("--bootstrap/--no-bootstrap",
        help="Auto-setup language env before dropping into shell.")] = True,
):
    """Drop into an interactive shell inside the lab.

    Examples:
      rudra lab shell mylab
      rudra lab shell mylab --no-bootstrap
    """
    cfg = load_lab(name)
    cfg.status = "running"
    save_lab(cfg)

    if bootstrap and cfg.source_path:
        from rudra_lab.env_setup import bootstrap_env
        extra = bootstrap_env(cfg)
        if extra:
            cfg.env_vars = {**cfg.env_vars, **extra}

    from rudra_lab.backends.dispatch import shell_in_lab
    exit_code = shell_in_lab(cfg)

    cfg.status = "stopped"
    save_lab(cfg)

    if cfg.disposable:
        console.print(f"\n[dim]Disposable lab — cleaning up...[/dim]")
        _destroy_lab_data(name)
        console.print(f"[green]✓ Lab '{name}' destroyed.[/green]")


# ── isolate ───────────────────────────────────────────────────────────────────

@app.command()
def isolate(
    path: Annotated[str, typer.Argument(help="Path to dir/file, or '-' to read from stdin.")],
    command: Annotated[Optional[str], typer.Option("--cmd", "-c", help="Command to run. Auto-detected if omitted.")] = None,
    tier: Annotated[Optional[str], typer.Option("--tier", "-t", help="Isolation tier. Auto-selects best if omitted.")] = None,
    internet: Annotated[str, typer.Option("--internet", help="Internet mode: no-internet | capture | denylist | allowlist.")] = "no-internet",
    allow_host: Annotated[Optional[list[str]], typer.Option("--allow-host", help="Allow host(s) — sets allowlist mode.")] = None,
    block_host: Annotated[Optional[list[str]], typer.Option("--block-host", help="Extra hosts to block.")] = None,
    snapshot: Annotated[bool, typer.Option("--snapshot/--no-snapshot", "-S", help="Before/after snapshots.")] = True,
    indicators: Annotated[bool, typer.Option("--indicators/--no-indicators", help="Scan for suspicious behaviour.")] = True,
    report: Annotated[Optional[list[str]], typer.Option("--report", "-r", help="Report formats: md json html.")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", "-n", help="Show what would happen, don't run.")] = False,
    keep: Annotated[bool, typer.Option("--keep", help="Keep lab after run.")] = False,
    timeout: Annotated[int, typer.Option("--timeout", help="Timeout in seconds (0 = no timeout).")] = 0,
):
    """One-shot: detect → isolate → run → analyse → report → destroy.

    Examples:
      rudra lab isolate ./suspicious.py
      rudra lab isolate ./project --internet denylist --report md --report html
      rudra lab isolate ./app --internet allowlist --allow-host pypi.org
      rudra lab isolate ./app --internet capture --report json
      curl https://example.com/script.sh | rudra lab isolate -
      rudra lab isolate ./thing --dry-run
    """
    import time as _time, sys as _sys

    # ── stdin ─────────────────────────────────────────────────────────────────
    stdin_mode = path.strip() == "-"
    src_path: Optional[Path] = None
    if stdin_mode:
        import tempfile as _tmp
        content = _sys.stdin.read()
        tmp = _tmp.NamedTemporaryFile(suffix=".sh", prefix="rudra-stdin-", delete=False, mode="w")
        tmp.write(content); tmp.flush()
        src_path = Path(tmp.name)
        command = command or f"bash {src_path}"
        console.print(f"[dim]stdin → {src_path}[/dim]")
    else:
        src_path = Path(path).resolve()
        if not src_path.exists():
            console.print(f"[red]Path '{path}' not found.[/red]")
            raise typer.Exit(1)

    # ── internet mode ─────────────────────────────────────────────────────────
    if allow_host:
        internet = "allowlist"
    net_mode = internet

    # ── auto-detect ───────────────────────────────────────────────────────────
    ptype = detect_project_type(src_path if src_path.is_dir() else src_path.parent)
    _AUTO = {
        ProjectType.PYTHON:  "python -m pytest -x 2>/dev/null || python main.py 2>/dev/null || ls -la",
        ProjectType.NODE:    "npm test 2>/dev/null || npm start",
        ProjectType.RUST:    "cargo test",
        ProjectType.RUBY:    "bundle exec rake 2>/dev/null || bundle exec ruby main.rb",
        ProjectType.GO:      "go test ./...",
        ProjectType.SHELL:   "bash install.sh 2>/dev/null || make 2>/dev/null || ls -la",
        ProjectType.UNKNOWN: "ls -la && file * 2>/dev/null || true",
    }
    run_cmd   = command or _AUTO.get(ptype, "ls -la")
    lab_name  = f"isolate-{src_path.name}-{datetime.now().strftime('%H%M%S')}"
    chosen_tier = best_tier(tier)

    from rudra_lab.helpers import TIER_SAFETY, TIER_DESCRIPTIONS
    sl  = TIER_SAFETY[chosen_tier]
    bar = "[green]" + "█"*sl + "[/green][dim]" + "░"*(5-sl) + "[/dim]"

    # ── dry run ───────────────────────────────────────────────────────────────
    if dry_run:
        console.print(Panel(
            f"[bold]Source:[/bold]    {src_path}\n"
            f"[bold]Command:[/bold]   {run_cmd}\n"
            f"[bold]Tier:[/bold]      {chosen_tier.value}  {bar}\n"
            f"[bold]Internet:[/bold]  {net_mode}"
            + (f"\n[bold]Allowlist:[/bold] {', '.join(allow_host)}" if allow_host else "")
            + (f"\n[bold]Block:[/bold]     {', '.join(block_host)}" if block_host else "")
            + f"\n[bold]Snapshots:[/bold] {snapshot}  [bold]Indicators:[/bold] {indicators}"
            + f"\n[bold]Reports:[/bold]   {', '.join(report) if report else 'none'}"
            + f"\n[bold]Keep:[/bold]      {keep}  [bold]Timeout:[/bold] {timeout}s",
            title="[bold yellow]⚗ dry run — nothing will execute[/bold yellow]",
            border_style="yellow",
        ))
        return

    # ── warn weak isolation ───────────────────────────────────────────────────
    console.print(Panel(
        f"[bold]Source:[/bold]  {src_path}\n"
        f"[bold]Command:[/bold] {run_cmd}\n"
        f"[bold]Tier:[/bold]    {chosen_tier.value}  {bar}\n"
        f"[bold]Internet:[/bold]{net_mode}"
        + (f"  [dim]allowlist: {', '.join(allow_host)}[/dim]" if allow_host else "")
        + f"\n[bold]Project:[/bold] {ptype.value}",
        title="[bold yellow]⚗ rudra lab isolate[/bold yellow]", border_style="yellow",
    ))
    if sl < 3:
        console.print(f"[yellow]⚠ Weak isolation ({chosen_tier.value}). Install Docker or firejail for stronger sandboxing.[/yellow]")
        if not typer.confirm("Continue anyway?", default=True):
            raise typer.Exit(0)

    # ── build lab config ──────────────────────────────────────────────────────
    cfg = LabConfig(
        name=lab_name, tier=chosen_tier.value, project_type=ptype.value,
        source_path=str(src_path), disposable=not keep,
        network_isolated=(net_mode == "no-internet"),
        readonly_mounts=[f"{src_path}:/lab/src"] if src_path.is_dir() else [],
        status="created",
        timeout=timeout,
    )
    save_lab(cfg)

    # ── start proxy ───────────────────────────────────────────────────────────
    from rudra_lab.proxy import ProxyConfig, start_proxy, stop_proxy, summarise_requests
    proxy_session = None
    if net_mode != "no-internet":
        pcfg = ProxyConfig(
            mode=net_mode, allowlist=allow_host or [],
            denylist_extra=block_host or [],
            log_path=LAB_DIR / f"proxy_{lab_name}.log",
        )
        proxy_session = start_proxy(pcfg)
        if proxy_session:
            cfg.env_vars.update(proxy_session.env_vars)
            # All tiers need host-network access so the lab process can reach
            # the proxy at 127.0.0.1. Docker uses --network=none when isolated;
            # unshare/firejail use --net/--net=none; nspawn uses --private-network.
            # Setting network_isolated=False disables all of these.
            cfg.network_isolated = False
        else:
            console.print("[yellow]Proxy failed — falling back to no-internet.[/yellow]")
            cfg.network_isolated = True

    # ── snapshot before ───────────────────────────────────────────────────────
    if snapshot:
        from rudra_lab.snapshot import take_snapshot
        take_snapshot(cfg, "before", paths=[str(src_path)] if src_path.is_dir() else [])

    # ── bootstrap env ─────────────────────────────────────────────────────────
    if src_path.is_dir():
        from rudra_lab.env_setup import bootstrap_env
        extra = bootstrap_env(cfg)
        if extra:
            cfg.env_vars = {**cfg.env_vars, **extra}

    # ── run ───────────────────────────────────────────────────────────────────
    from rudra_lab.backends.dispatch import run_in_lab
    t0 = _time.time()
    exit_code, output = run_in_lab(cfg, run_cmd, capture_output=True)
    duration = _time.time() - t0

    # ── stop proxy ────────────────────────────────────────────────────────────
    proxy_requests = stop_proxy(proxy_session)
    proxy_summary  = summarise_requests(proxy_requests) if proxy_requests else None

    # ── snapshot after + structured diff ─────────────────────────────────────
    fs_diff: dict = {}
    if snapshot:
        from rudra_lab.snapshot import take_snapshot, diff_snapshots, SNAP_DIR
        import json as _json
        take_snapshot(cfg, "after", paths=[str(src_path)] if src_path.is_dir() else [])
        bp = SNAP_DIR / f"{lab_name}_before.json"
        ap = SNAP_DIR / f"{lab_name}_after.json"
        if bp.exists() and ap.exists():
            bd = _json.loads(bp.read_text()); ad = _json.loads(ap.read_text())
            fb = bd.get("fs",{}); fa = ad.get("fs",{})
            fs_diff = {
                "added":    {k:v for k,v in fa.items() if k not in fb},
                "removed":  {k:v for k,v in fb.items() if k not in fa},
                "modified": {k:v for k,v in fa.items() if k in fb and fb[k]!=v},
            }
        diff_snapshots(cfg, "before", "after")

    # ── indicators ────────────────────────────────────────────────────────────
    inds = []
    if indicators:
        from rudra_lab.indicators import scan, print_indicators
        inds = scan(output=output, fs_diff=fs_diff,
                    proxy_requests=proxy_requests, source_path=str(src_path))
        print_indicators(inds, proxy_summary)

    # ── log ───────────────────────────────────────────────────────────────────
    log_file = log_run(lab_name, run_cmd, output, exit_code)
    console.print(f"[dim]Log: {log_file}[/dim]")

    # ── reports ───────────────────────────────────────────────────────────────
    if report:
        from rudra_lab.report import RunReport
        rpt = RunReport(lab_name=lab_name, command=run_cmd, exit_code=exit_code,
                        output=output, tier=chosen_tier.value, source_path=str(src_path),
                        internet_mode=net_mode, indicators=inds,
                        proxy_summary=proxy_summary, fs_diff=fs_diff,
                        duration_s=duration, cfg=cfg)
        saved = rpt.save(formats=report, name_hint=src_path.name)
        console.print("\n[bold]Reports:[/bold]")
        for fmt, p in saved.items():
            console.print(f"  [cyan]{fmt}[/cyan]  {p}")

    # ── result ────────────────────────────────────────────────────────────────
    console.print()
    if exit_code == 0:
        console.print(f"[bold green]✓ Exited 0[/bold green]  ({duration:.1f}s)")
    else:
        console.print(f"[bold red]✗ Exited {exit_code}[/bold red]  ({duration:.1f}s)")
        _hint_exit_code(exit_code, chosen_tier)

    if stdin_mode and src_path and src_path.exists():
        src_path.unlink(missing_ok=True)

    if keep:
        console.print(f"[dim]Lab kept as '{lab_name}'. Destroy: rudra lab destroy {lab_name}[/dim]")
    else:
        _destroy_lab_data(lab_name)
        console.print("[dim]Lab destroyed.[/dim]")

    raise typer.Exit(exit_code)


@app.command()
def destroy(
    name: Annotated[str, typer.Argument(help="Lab name.")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation.")] = False,
):
    """Destroy a lab and all its data.

    Examples:
      rudra lab destroy mylab
      rudra lab destroy mylab --yes
    """
    if not (LABS_DIR / name).exists():
        console.print(f"[yellow]Lab '{name}' not found.[/yellow]")
        raise typer.Exit(0)

    if not yes and not typer.confirm(f"Destroy lab '{name}' and all its data?", default=False):
        raise typer.Exit(0)

    cfg = load_lab(name)
    from rudra_lab.backends.dispatch import teardown_lab
    teardown_lab(cfg)
    _destroy_lab_data(name)
    console.print(f"[bold green]✓ Lab '{name}' destroyed.[/bold green]")


# ── list ──────────────────────────────────────────────────────────────────────

@app.command(name="list")
def list_cmd():
    """List all labs with status, tier, and last run."""
    labs = list_labs()
    if not labs:
        console.print("[dim]No labs found. Create one with: rudra lab create <name>[/dim]")
        return

    table = Table(show_header=True, header_style="bold dim", box=None, padding=(0, 2))
    table.add_column("name",       style="bold cyan")
    table.add_column("tier",       no_wrap=True)
    table.add_column("status",     no_wrap=True)
    table.add_column("network",    no_wrap=True)
    table.add_column("runs",       no_wrap=True, style="dim")
    table.add_column("last run",   style="dim")
    table.add_column("disposable", no_wrap=True, style="dim")

    for lab in labs:
        tc = TIER_COLORS.get(lab.tier, "white")
        sc = STATUS_COLORS.get(lab.status, "white")
        net = "[red]isolated[/red]" if lab.network_isolated else "[yellow]shared[/yellow]"
        last = lab.last_run[:16].replace("T", " ") if lab.last_run else "[dim]never[/dim]"
        table.add_row(
            lab.name,
            f"[{tc}]{lab.tier}[/{tc}]",
            f"[{sc}]{lab.status}[/{sc}]",
            net,
            str(lab.run_count),
            last,
            "yes" if lab.disposable else "no",
        )

    console.print()
    console.print(table)
    console.print()


# ── inspect ───────────────────────────────────────────────────────────────────

@app.command()
def inspect(
    name: Annotated[str, typer.Argument(help="Lab name.")],
):
    """Show full lab config, mounts, env vars, and run history."""
    cfg = load_lab(name)

    console.print()
    table = Table(box=None, show_header=False, padding=(0, 2))
    table.add_column(style="bold dim", no_wrap=True)
    table.add_column()

    tc = TIER_COLORS.get(cfg.tier, "white")
    sc = STATUS_COLORS.get(cfg.status, "white")

    table.add_row("name",        f"[bold cyan]{cfg.name}[/bold cyan]")
    table.add_row("tier",        f"[{tc}]{cfg.tier}[/{tc}]")
    table.add_row("status",      f"[{sc}]{cfg.status}[/{sc}]")
    table.add_row("project",     cfg.project_type)
    table.add_row("network",     "isolated" if cfg.network_isolated else "shared")
    table.add_row("disposable",  str(cfg.disposable))
    table.add_row("created",     cfg.created_at[:16].replace("T", " "))
    table.add_row("last run",    cfg.last_run[:16].replace("T", " ") if cfg.last_run else "never")
    table.add_row("run count",   str(cfg.run_count))

    if cfg.source_path:
        table.add_row("source",  cfg.source_path)
    if cfg.docker_image and cfg.tier == "docker":
        table.add_row("image",   cfg.docker_image)
    if cfg.readonly_mounts:
        table.add_row("mounts (ro)", "\n".join(cfg.readonly_mounts))
    if cfg.writable_mounts:
        table.add_row("mounts (rw)", "\n".join(cfg.writable_mounts))
    if cfg.port_bindings:
        table.add_row("ports",   "\n".join(cfg.port_bindings))
    if cfg.env_vars:
        ev = "\n".join(f"{k}={v}" for k, v in cfg.env_vars.items())
        table.add_row("env vars", ev)

    console.print(Panel(table, title=f"[bold]Lab: {cfg.name}[/bold]", border_style="cyan"))

    # Recent logs
    logs = sorted(LOGS_DIR.glob(f"{name}_*.log"), reverse=True)[:5]
    if logs:
        console.print("[bold dim]Recent run logs:[/bold dim]")
        for log in logs:
            console.print(f"  [dim]{log.name}[/dim]")
    console.print()


# ── snapshot commands ─────────────────────────────────────────────────────────

@app.command()
def snapshot(
    name: Annotated[str, typer.Argument(help="Lab name.")],
    tag: Annotated[str, typer.Argument(help="Snapshot tag/name.")],
    paths: Annotated[Optional[list[str]], typer.Option("--path", "-p",
        help="Paths to include in snapshot.")] = None,
):
    """Take a snapshot of the current lab state."""
    cfg = load_lab(name)
    from rudra_lab.snapshot import take_snapshot
    take_snapshot(cfg, tag, paths=paths)


@app.command()
def diff(
    name: Annotated[str, typer.Argument(help="Lab name.")],
    before: Annotated[str, typer.Argument(help="'Before' snapshot tag.")],
    after: Annotated[str, typer.Argument(help="'After' snapshot tag.")],
):
    """Diff two snapshots to see what changed between runs."""
    cfg = load_lab(name)
    from rudra_lab.snapshot import diff_snapshots
    diff_snapshots(cfg, before, after)


@app.command()
def snapshots(
    name: Annotated[str, typer.Argument(help="Lab name.")],
):
    """List all snapshots for a lab."""
    from rudra_lab.snapshot import list_snapshots
    list_snapshots(name)


# ── ports ─────────────────────────────────────────────────────────────────────

@app.command()
def ports(
    name: Annotated[str, typer.Argument(help="Lab name.")],
    add: Annotated[Optional[str], typer.Option("--add", "-a",
        help="Add port binding (host:container).")] = None,
    remove: Annotated[Optional[str], typer.Option("--remove", "-r",
        help="Remove port binding.")] = None,
):
    """Manage port bindings for a lab.

    Examples:
      rudra lab ports mylab                 # list bindings
      rudra lab ports mylab --add 8080:80   # add binding
      rudra lab ports mylab --remove 8080:80
    """
    cfg = load_lab(name)

    if add:
        if add not in cfg.port_bindings:
            cfg.port_bindings.append(add)
            save_lab(cfg)
            console.print(f"[green]✓ Added port binding {add}.[/green]")
        else:
            console.print(f"[dim]Binding {add} already set.[/dim]")
        return

    if remove:
        if remove in cfg.port_bindings:
            cfg.port_bindings.remove(remove)
            save_lab(cfg)
            console.print(f"[green]✓ Removed {remove}.[/green]")
        else:
            console.print(f"[yellow]{remove} not in bindings.[/yellow]")
        return

    if cfg.port_bindings:
        console.print(f"\n[bold]Port bindings for '{name}':[/bold]")
        for b in cfg.port_bindings:
            host, _, cont = b.partition(":")
            console.print(f"  [cyan]{host}[/cyan] → [yellow]{cont}[/yellow]")
        console.print()
    else:
        console.print(f"[dim]No port bindings for '{name}'.[/dim]")


# ── logs ──────────────────────────────────────────────────────────────────────

@app.command()
def logs(
    name: Annotated[str, typer.Argument(help="Lab name.")],
    n: Annotated[int, typer.Option("--count", "-n", help="Number of logs to show.")] = 5,
    tail: Annotated[bool, typer.Option("--tail", help="Show last log content.")] = False,
):
    """Show run logs for a lab.

    Examples:
      rudra lab logs mylab
      rudra lab logs mylab --tail     # show last log content
    """
    lab_logs = sorted(LOGS_DIR.glob(f"{name}_*.log"), reverse=True)[:n]
    if not lab_logs:
        console.print(f"[dim]No logs for lab '{name}'.[/dim]")
        return

    if tail:
        console.print(lab_logs[0].read_text())
        return

    console.print(f"\n[bold]Run logs for '{name}':[/bold]")
    for log in lab_logs:
        lines = log.read_text().splitlines()
        cmd_line   = next((l for l in lines if l.startswith("Command:")),   "")
        exit_line  = next((l for l in lines if l.startswith("Exit code:")), "")
        ts_line    = next((l for l in lines if l.startswith("Timestamp:")), "")
        exit_code  = exit_line.replace("Exit code:", "").strip()
        color      = "green" if exit_code == "0" else "red"
        console.print(f"  [{color}]{exit_code:>4}[/{color}]  [dim]{ts_line.replace('Timestamp:','').strip()}[/dim]  {cmd_line.replace('Command:','').strip()[:60]}")
    console.print()


# ── clean ─────────────────────────────────────────────────────────────────────

@app.command()
def clean(
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation.")] = False,
):
    """Remove all stopped/disposable labs and their data."""
    labs = list_labs()
    to_clean = [l for l in labs if l.disposable and l.status in ("stopped", "created")]

    if not to_clean:
        console.print("[dim]No disposable/stopped labs to clean.[/dim]")
        return

    console.print(f"[yellow]Labs to remove ({len(to_clean)}):[/yellow]")
    for lab in to_clean:
        console.print(f"  [dim]{lab.name}[/dim]  ({lab.status})")

    if not yes and not typer.confirm(f"\nRemove {len(to_clean)} labs?", default=True):
        raise typer.Exit(0)

    for lab in to_clean:
        from rudra_lab.backends.dispatch import teardown_lab
        teardown_lab(lab)
        _destroy_lab_data(lab.name)

    console.print(f"[bold green]✓ Cleaned {len(to_clean)} lab(s).[/bold green]")


# ── tiers ─────────────────────────────────────────────────────────────────────

@app.command()
def tiers():
    """Show available isolation tiers on this machine."""
    from rudra_lab.helpers import TIER_SAFETY, TIER_DESCRIPTIONS

    available = detect_tiers()
    all_tiers = list(Tier)

    console.print()
    table = Table(show_header=True, header_style="bold dim", box=None, padding=(0, 2))
    table.add_column("tier",        style="bold")
    table.add_column("safety",      no_wrap=True)
    table.add_column("available",   no_wrap=True)
    table.add_column("description", style="dim")

    for t in all_tiers:
        s = TIER_SAFETY[t]
        bar = "[green]" + "█" * s + "[/green][dim]" + "░" * (5 - s) + "[/dim]"
        avail = "[green]yes[/green]" if t in available else "[red]no[/red]"
        tc = TIER_COLORS.get(t.value, "white")
        table.add_row(f"[{tc}]{t.value}[/{tc}]", bar, avail, TIER_DESCRIPTIONS[t])

    console.print(table)
    console.print()
    console.print(f"[dim]Best available: [bold]{available[0].value}[/bold][/dim]")
    console.print()


# ── cleanup & prune ───────────────────────────────────────────────────────────

@app.command(name="cleanup")
@app.command(name="prune")
def cleanup_cmd(
    days: Annotated[int, typer.Option("--days", "-d", help="Max retention in days for stopped labs and logs.")] = 7,
    all_stopped: Annotated[bool, typer.Option("--all-stopped", "-a", help="Clean all stopped/destroyed labs immediately.")] = False,
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation prompt.")] = False,
):
    """Auto-clean expired/dead lab containers, temporary mounts, and old run logs."""
    from rudra_lab.helpers import cleanup_expired_labs_and_logs
    console.print(Panel.fit(f"[bold cyan]🧹 Rudra Lab Housekeeping & Pruning[/bold cyan]\n[dim]Purging expired lab workspaces and run logs older than {days} days...[/dim]", border_style="cyan"))

    if not force and all_stopped:
        if not typer.confirm("Purge ALL stopped labs immediately?"):
            console.print("[yellow]Cleanup aborted.[/yellow]")
            return

    cleaned_labs, cleaned_logs = cleanup_expired_labs_and_logs(max_age_days=days, clean_all_stopped=all_stopped)
    console.print(f"[bold green]✓ Cleanup complete! Purged {cleaned_labs} lab workspace(s) and {cleaned_logs} log file(s).[/bold green]")


# ── internal helpers ──────────────────────────────────────────────────────────

def _destroy_lab_data(name: str) -> None:
    """Remove the lab directory and any snapshots from disk."""
    import shutil as _shutil
    d = lab_dir(name)
    if d.exists():
        _shutil.rmtree(d, ignore_errors=True)
    # Remove snapshots for this lab
    from rudra_lab.snapshot import SNAP_DIR
    for snap in SNAP_DIR.glob(f"{name}_*.json"):
        snap.unlink(missing_ok=True)
