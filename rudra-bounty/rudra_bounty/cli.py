"""CLI interface for Rudra Bug Bounty Hunter ('rudra hunt' / 'rudra bounty')."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from rudra_bounty import audit, findings, report, scope, surface

console = Console()
app = typer.Typer(
    name="hunt",
    help="🎯 Bug bounty hunter — scope management, passive surface discovery, posture audit, and reporting.",
    no_args_is_help=True,
)

scope_app = typer.Typer(help="🛡️ Scope & Rules of Engagement manager.", no_args_is_help=True)
track_app = typer.Typer(help="📋 Local finding tracker & triage lifecycle.", no_args_is_help=True)
report_app = typer.Typer(help="📝 Standard report generator & CVSS v3.1 calculator.", no_args_is_help=True)

app.add_typer(scope_app, name="scope")
app.add_typer(track_app, name="track")
app.add_typer(track_app, name="findings")
app.add_typer(report_app, name="report")


def _t():
    try:
        from rudra.theme import get_current_theme
        return get_current_theme()
    except Exception:
        from rudra.theme import ThemeConfig
        return ThemeConfig()


def _guard_target(target: str) -> bool:
    """Validate target against active scope if one is set."""
    th = _t()
    res = scope.check_target(target)
    if not res["allowed"]:
        console.print(
            Panel(
                f"[bold {th.error}]⚠ TARGET OUT OF SCOPE[/bold {th.error}]\n\n"
                f"{res['reason']}\n\n"
                f"[{th.dim}]To manage program scope, run: [bold]rudra hunt scope list[/bold][/{th.dim}]",
                title=f"[{th.error}]Scope Guard Check[/{th.error}]",
                border_style=th.error,
            )
        )
        return False
    if res.get("program"):
        console.print(f"[{th.dim}]🛡️ Scope verified: {res['reason']}[/{th.dim}]\n")
    return True


# ── Scope Commands ──────────────────────────────────────────────────────────

@scope_app.command(name="list")
def scope_list():
    """List all configured bug bounty programs and active scopes."""
    th = _t()
    programs = scope.list_programs()
    if not programs:
        console.print(f"[{th.warning}]No bounty programs configured yet.[/{th.warning}]")
        console.print(f"[{th.dim}]Add one with: [bold]rudra hunt scope add <name> --in \"*.example.com\"[/bold][/{th.dim}]")
        return

    table = Table(title=f"[{th.table_header}]{th.prompt_char} Bug Bounty Programs & Scopes[/{th.table_header}]", border_style=th.panel_border, show_lines=True)
    table.add_column("Program", style=f"bold {th.primary}")
    table.add_column("Platform", style=th.secondary)
    table.add_column("Active", justify="center")
    table.add_column("In-Scope Rules", style=th.success)
    table.add_column("Out-of-Scope (Blocklist)", style=th.error)

    for p in programs:
        active_mark = f"[bold {th.success}]✓ ACTIVE[/bold {th.success}]" if p.get("active") else f"[{th.dim}]·[/{th.dim}]"
        in_s = "\n".join(p.get("in_scope", [])) or "—"
        out_s = "\n".join(p.get("out_of_scope", [])) or "—"
        table.add_row(p["name"], p.get("platform", "—"), active_mark, in_s, out_s)

    console.print(table)


@scope_app.command(name="add")
def scope_add(
    name: Annotated[str, typer.Argument(help="Program name (e.g. shopify, tesla, acme).")],
    in_scope: Annotated[list[str], typer.Option("--in", "-i", help="In-scope domain/wildcard pattern (can repeat).")] = [],
    out_of_scope: Annotated[list[str], typer.Option("--out", "-o", help="Explicitly excluded/out-of-scope pattern (can repeat).")] = [],
    platform: Annotated[str, typer.Option("--platform", "-p", help="Platform: HackerOne, Bugcrowd, Intigriti, Private.")] = "HackerOne",
    notes: Annotated[str, typer.Option("--notes", "-n", help="Program rules or payout notes.")] = "",
):
    """Add a new bug bounty program with scope rules."""
    th = _t()
    if not in_scope:
        console.print(f"[{th.error}]Must provide at least one --in pattern (e.g. --in '*.example.com')[/{th.error}]")
        raise typer.Exit(1)

    scope.add_program(name, platform, in_scope, out_of_scope, notes=notes)
    console.print(f"[bold {th.success}]✓ Program '{name}' configured successfully![/bold {th.success}]")
    console.print(f"[{th.dim}]To activate: [bold]rudra hunt scope set-active {name}[/bold][/{th.dim}]")


@scope_app.command(name="set-active")
def scope_set_active(name: Annotated[str, typer.Argument(help="Program name to activate.")]):
    """Set the currently active target program."""
    th = _t()
    if scope.set_active(name):
        console.print(f"[bold {th.success}]✓ Active program set to: {name}[/bold {th.success}]")
    else:
        console.print(f"[bold {th.error}]Program '{name}' not found.[/{th.error}]")


@scope_app.command(name="check")
def scope_check(target: Annotated[str, typer.Argument(help="Domain or URL to test against scope.")]):
    """Verify if a specific domain or URL is within scope."""
    th = _t()
    res = scope.check_target(target)
    if res["allowed"]:
        console.print(f"[bold {th.success}]✓ {res['reason']}[/bold {th.success}]")
    else:
        console.print(f"[bold {th.error}]✖ {res['reason']}[/bold {th.error}]")


# ── Surface Discovery ───────────────────────────────────────────────────────

@app.command(name="surface")
def surface_cmd(
    domain: Annotated[str, typer.Argument(help="Apex or root domain to map (e.g. example.com).")],
    skip_scope: Annotated[bool, typer.Option("--skip-scope", help="Bypass scope guard check.")] = False,
):
    """Passively map attack surface via Certificate Transparency logs and DNS."""
    th = _t()
    if not skip_scope and not _guard_target(domain):
        return

    console.print(f"[bold {th.primary}]{th.prompt_char} Mapping passive surface for {domain}...[/bold {th.primary}]\n")

    # 1. CT logs
    ct_data = surface.ct_log_subdomains(domain)
    subdomains = ct_data.get("subdomains", [])

    table = Table(title=f"[{th.table_header}]Discovered Subdomains via CT Logs ({len(subdomains)})[/{th.table_header}]", border_style=th.panel_border)
    table.add_column("Subdomain", style=f"bold {th.primary}")
    for sub in subdomains[:30]:
        table.add_row(sub)
    if len(subdomains) > 30:
        table.add_row(f"[{th.dim}]... and {len(subdomains) - 30} more (see full export)[/{th.dim}]")
    console.print(table)
    console.print()

    # 2. DNS profile & Takeovers
    dns = surface.dns_profile(domain)
    dns_table = Table(title=f"[{th.table_header}]Core DNS Records[/{th.table_header}]", border_style=th.panel_border)
    dns_table.add_column("Type", style="bold")
    dns_table.add_column("Records")
    for rtype, recs in dns.get("records", {}).items():
        dns_table.add_row(rtype, "\n".join(recs[:4]))
    console.print(dns_table)
    console.print()

    # Takeover alerts
    takeovers = dns.get("takeover_risks", [])
    if takeovers:
        to_table = Table(title=f"[bold {th.error}]⚠ Potential Subdomain Takeover Indicators[/bold {th.error}]", border_style=th.error)
        to_table.add_column("CNAME")
        to_table.add_column("Service Provider")
        to_table.add_column("Risk")
        to_table.add_column("Note")
        for to in takeovers:
            to_table.add_row(to["cname"], to["provider"], f"[bold {th.error}]{to['risk']}[/bold {th.error}]", to["note"])
        console.print(to_table)
        console.print()

    # Email security posture
    es = dns.get("email_security", {})
    console.print(
        Panel(
            f"[bold]SPF Record:[/bold]   {es.get('spf')}\n"
            f"[bold]DMARC Record:[/bold] {es.get('dmarc')}",
            title=f"[{th.primary}]Email Security Posture[/{th.primary}]",
            border_style=th.panel_border,
        )
    )


# ── Audit Commands ──────────────────────────────────────────────────────────

@app.command(name="audit")
def audit_cmd(
    target: Annotated[str, typer.Argument(help="Target URL or domain (e.g. example.com or https://example.com).")],
    skip_scope: Annotated[bool, typer.Option("--skip-scope", help="Bypass scope guard.")] = False,
):
    """Run comprehensive defensive posture audit (Headers, CORS, TLS, Policy endpoints)."""
    th = _t()
    if not skip_scope and not _guard_target(target):
        return

    url = target if target.startswith(("http://", "https://")) else f"https://{target}"
    console.print(f"[bold {th.primary}]{th.prompt_char} Auditing defensive posture for {url}...[/bold {th.primary}]\n")

    # 1. Headers
    hdr = audit.audit_headers(url)
    if "error" in hdr:
        console.print(f"[bold {th.error}]✖ {hdr['error']}[/bold {th.error}]")
        return

    h_table = Table(title=f"[{th.table_header}]HTTP Security Headers (Grade: {hdr['grade']} — {hdr['score']}%)[/{th.table_header}]", border_style=th.panel_border)
    h_table.add_column("Header", style="bold")
    h_table.add_column("Status", justify="center")
    h_table.add_column("Current Value / Remediation")

    for name, val in hdr.get("present_headers", {}).items():
        h_table.add_row(name, f"[{th.success}]✓ OK[/{th.success}]", val[:60])
    for name, advice in hdr.get("missing_headers", {}).items():
        h_table.add_row(name, f"[{th.error}]MISSING[/{th.error}]", f"[{th.dim}]{advice}[/{th.dim}]")
    console.print(h_table)
    console.print()

    # 2. CORS
    cors = audit.audit_cors(url)
    if cors.get("vulnerable"):
        c_table = Table(title=f"[bold {th.warning}]⚠ CORS Policy Observations[/bold {th.warning}]", border_style=th.warning)
        c_table.add_column("Tested Origin")
        c_table.add_column("Allowed Origin")
        c_table.add_column("Credentials")
        c_table.add_column("Severity")
        for f in cors.get("findings", []):
            c_table.add_row(f["origin_tested"], f["acao"], str(f["credentials_allowed"]), f["severity"])
        console.print(c_table)
        console.print()

    # 3. TLS
    tls = audit.audit_tls(url)
    if "error" not in tls:
        t_panel = Panel(
            f"[bold]Subject:[/bold]        {tls.get('subject')}\n"
            f"[bold]Issuer:[/bold]         {tls.get('issuer')}\n"
            f"[bold]Expires:[/bold]        {tls.get('expires_date')} ({tls.get('days_remaining')} days remaining)\n"
            f"[bold]TLS Version:[/bold]    {tls.get('tls_version')}\n"
            f"[bold]Cipher Suite:[/bold]   {tls.get('cipher')}\n"
            f"[bold]SANs Count:[/bold]     {tls.get('sans_count')}",
            title=f"[{th.primary}]TLS / SSL Certificate Health[/{th.primary}]",
            border_style=th.panel_border,
        )
        console.print(t_panel)
        console.print()

    # 4. Policy endpoints
    pol = audit.audit_policy_endpoints(url)
    if pol.get("endpoints"):
        p_table = Table(title=f"[{th.table_header}]Policy & Disclosure Endpoints[/{th.table_header}]", border_style=th.panel_border)
        p_table.add_column("Endpoint", style=f"bold {th.primary}")
        p_table.add_column("HTTP Status", justify="center")
        p_table.add_column("Snippet", style=th.dim)
        for ep in pol["endpoints"]:
            p_table.add_row(ep["path"], str(ep["status"]), ep["snippet"][:80])
        console.print(p_table)


@app.command(name="headers")
def headers_cmd(url: Annotated[str, typer.Argument(help="Target URL.")]):
    """Audit HTTP security headers and display compliance grade."""
    th = _t()
    res = audit.audit_headers(url)
    if "error" in res:
        console.print(f"[bold {th.error}]✖ {res['error']}[/bold {th.error}]")
        return
    table = Table(title=f"[{th.table_header}]Security Headers: {res['grade']} ({res['score']}%)[/{th.table_header}]", border_style=th.panel_border)
    table.add_column("Header")
    table.add_column("Status")
    table.add_column("Details")
    for k, v in res.get("present_headers", {}).items():
        table.add_row(k, f"[{th.success}]✓[/{th.success}]", v[:60])
    for k, adv in res.get("missing_headers", {}).items():
        table.add_row(k, f"[{th.error}]MISSING[/{th.error}]", adv)
    console.print(table)


# ── Tracking / Finding Lifecycle ────────────────────────────────────────────

@track_app.command(name="add")
def track_add(
    title: Annotated[str, typer.Argument(help="Finding summary title.")],
    target: Annotated[str, typer.Argument(help="Affected asset/endpoint.")],
    severity: Annotated[str, typer.Option("--severity", "-s", help="CRITICAL, HIGH, MEDIUM, LOW, INFO.")] = "MEDIUM",
    category: Annotated[str, typer.Option("--category", "-c", help="CWE or vulnerability class.")] = "Security Misconfiguration",
    desc: Annotated[str, typer.Option("--desc", "-d", help="Detailed finding description.")] = "",
    remediation: Annotated[str, typer.Option("--fix", "-f", help="Recommended defensive patch/remediation.")] = "",
):
    """Record a new security finding into your local tracker."""
    th = _t()
    active = scope.get_active_program()
    prog_name = active[0] if active else "default"
    item = findings.add_finding(title, target, severity, category, desc, remediation, program=prog_name)
    console.print(f"[bold {th.success}]✓ Finding logged [ID: {item['id']}][/bold {th.success}] for program '{prog_name}'")


@track_app.command(name="list")
def track_list(
    program: Annotated[Optional[str], typer.Option("--program", "-p", help="Filter by program.")] = None,
    severity: Annotated[Optional[str], typer.Option("--severity", "-s", help="Filter by severity.")] = None,
):
    """List all tracked findings in your local workspace."""
    th = _t()
    items = findings.list_findings(program=program, severity=severity)
    if not items:
        console.print(f"[{th.warning}]No findings logged yet.[/{th.warning}] Use [bold]rudra hunt track add[/bold] to log one.")
        return

    table = Table(title=f"[{th.table_header}]{th.prompt_char} Tracked Findings ({len(items)})[/{th.table_header}]", border_style=th.panel_border, show_lines=True)
    table.add_column("ID", style="dim", no_wrap=True)
    table.add_column("Severity", no_wrap=True)
    table.add_column("Title", style=f"bold {th.primary}")
    table.add_column("Target")
    table.add_column("Status", no_wrap=True)
    table.add_column("Program", style=th.secondary)

    sev_colors = {"CRITICAL": "bold red", "HIGH": "red", "MEDIUM": "yellow", "LOW": "cyan", "INFO": "dim"}
    for i in items:
        sc = sev_colors.get(i["severity"], "white")
        table.add_row(i["id"], f"[{sc}]{i['severity']}[/{sc}]", i["title"], i["target"], i["status"], i["program"])
    console.print(table)


@track_app.command(name="status")
def track_status(
    finding_id: Annotated[str, typer.Argument(help="Finding ID.")],
    status: Annotated[str, typer.Argument(help="New status: discovered, triaged, reported, accepted, resolved, duplicate.")],
    note: Annotated[str, typer.Option("--note", "-n", help="Optional status update note.")] = "",
):
    """Update lifecycle status of a tracked finding."""
    th = _t()
    if findings.update_finding_status(finding_id, status, note):
        console.print(f"[bold {th.success}]✓ Finding {finding_id} status updated to: {status}[/bold {th.success}]")
    else:
        console.print(f"[bold {th.error}]Finding {finding_id} not found.[/{th.error}]")


# ── Report Generation ───────────────────────────────────────────────────────

@report_app.command(name="cvss")
def cvss_calc(
    av: Annotated[str, typer.Option(help="Attack Vector: N (Network), A (Adjacent), L (Local), P (Physical).")] = "N",
    ac: Annotated[str, typer.Option(help="Attack Complexity: L (Low), H (High).")] = "L",
    pr: Annotated[str, typer.Option(help="Privileges Required: N (None), L (Low), H (High).")] = "N",
    ui: Annotated[str, typer.Option(help="User Interaction: N (None), R (Required).")] = "N",
    s: Annotated[str, typer.Option(help="Scope: U (Unchanged), C (Changed).")] = "U",
    c: Annotated[str, typer.Option(help="Confidentiality: N (None), L (Low), H (High).")] = "L",
    i: Annotated[str, typer.Option(help="Integrity: N (None), L (Low), H (High).")] = "L",
    a: Annotated[str, typer.Option(help="Availability: N (None), L (Low), H (High).")] = "N",
):
    """Compute standard CVSS v3.1 score and vector string."""
    th = _t()
    score, vector, sev = report.calculate_cvss31(av, ac, pr, ui, s, c, i, a)
    console.print(
        Panel(
            f"[bold]Base Score:[/bold]       [bold {th.primary}]{score}[/bold {th.primary}]\n"
            f"[bold]Severity:[/bold]         [bold {th.primary}]{sev}[/bold {th.primary}]\n"
            f"[bold]CVSS Vector:[/bold]      `{vector}`",
            title=f"[{th.primary}]CVSS v3.1 Calculator[/{th.primary}]",
            border_style=th.panel_border,
        )
    )


@report_app.command(name="export")
def report_export(
    finding_id: Annotated[str, typer.Argument(help="Tracked finding ID to export.")],
    output: Annotated[Optional[Path], typer.Option("--output", "-o", help="Output .md file path.")] = None,
):
    """Generate a full HackerOne/Bugcrowd markdown report from a tracked finding."""
    th = _t()
    item = findings.get_finding(finding_id)
    if not item:
        console.print(f"[bold {th.error}]Finding {finding_id} not found.[/{th.error}]")
        raise typer.Exit(1)

    md_content = report.generate_report_markdown(
        title=item["title"],
        target=item["target"],
        vulnerability_type=item.get("category", "Security Misconfiguration"),
        severity=item["severity"],
        summary=item.get("description", ""),
        remediation=item.get("remediation", ""),
        program=item.get("program", ""),
    )

    if output:
        output.write_text(md_content, encoding="utf-8")
        console.print(f"[bold {th.success}]✓ Report saved to: {output}[/bold {th.success}]")
    else:
        console.print(Markdown(md_content))
