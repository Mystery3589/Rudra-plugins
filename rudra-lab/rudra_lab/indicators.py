"""Post-run suspicious behaviour / malware indicator detection."""

from __future__ import annotations
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table

console = Console()


@dataclass
class Indicator:
    severity: str
    category: str
    title: str
    detail: str


_SEV_COLOR = {"critical":"bold red","high":"red","medium":"yellow","low":"dim yellow","info":"dim"}
_SEV_SCORE = {"critical":100,"high":40,"medium":15,"low":5,"info":1}

_SENSITIVE_PATHS = [
    re.compile(r"^/etc/"), re.compile(r"^/usr/(bin|sbin|lib)/"),
    re.compile(r"^/root/"), re.compile(r"\.ssh/"), re.compile(r"\.gnupg/"),
    re.compile(r"\.(bash_history|zsh_history|fish_history)$"),
    re.compile(r"crontab|cron\.d"), re.compile(r"\.bashrc|\.zshrc|\.profile"),
    re.compile(r"sudoers"), re.compile(r"shadow|passwd"),
    re.compile(r"authorized_keys"), re.compile(r"\.aws/credentials"),
    re.compile(r"\.config/.*token"),
]

_SUSPICIOUS_EXEC = re.compile(
    r"(backdoor|exploit|payload|reverse|rat|keylog|miner|stealer|"
    r"dropper|loader|inject|rootkit|pwn|xmrig|monero)",
    re.IGNORECASE,
)

_OUTPUT_PATTERNS = [
    (re.compile(r"chmod\s+[0-7]*7\s+",re.I),              "medium",   "chmod +x during run"),
    (re.compile(r"curl\s+.*\|\s*(ba)?sh",re.I),            "high",     "curl|sh pipe pattern"),
    (re.compile(r"wget\s+.*\|\s*(ba)?sh",re.I),            "high",     "wget|sh pipe pattern"),
    (re.compile(r"base64\s+-d",re.I),                      "medium",   "base64 decode during run"),
    (re.compile(r"eval\s*\(\s*base64",re.I),               "high",     "eval(base64(...)) pattern"),
    (re.compile(r"rm\s+-rf\s+/",re.I),                     "critical", "rm -rf / attempt"),
    (re.compile(r"dd\s+if=/dev/(zero|random|urandom)",re.I),"high",    "dd wipe pattern"),
    (re.compile(r"nc\s+-[lne]",re.I),                      "high",     "netcat listener/exec"),
    (re.compile(r"/dev/tcp/",re.I),                        "high",     "bash /dev/tcp redirect"),
    (re.compile(r"crontab\s+-[le]",re.I),                  "medium",   "crontab modification"),
    (re.compile(r"useradd|adduser|passwd\s+root",re.I),    "high",     "user account manipulation"),
    (re.compile(r"iptables|nftables|ufw\s+",re.I),         "medium",   "firewall rule modification"),
    (re.compile(r"nmap|masscan|zmap",re.I),                "high",     "network scanner invocation"),
    (re.compile(r"\$\(curl|\$\(wget",re.I),                "high",     "command substitution download"),
    (re.compile(r"sudo\s+",re.I),                          "low",      "sudo invocation"),
    (re.compile(r"python.*-c.*import\s+socket",re.I),      "medium",   "python socket in -c arg"),
]

_ENV_RE = re.compile(
    r"\$\{?(AWS_SECRET|AWS_ACCESS|GITHUB_TOKEN|NPM_TOKEN|PYPI_TOKEN|"
    r"DATABASE_URL|DB_PASS|SECRET_KEY|API_KEY|PRIVATE_KEY|"
    r"GH_TOKEN|GITLAB_TOKEN|DOCKER_TOKEN)\}?", re.IGNORECASE,
)

_SUSPICIOUS_HOSTS = re.compile(
    r"(pastebin\.com|pastie\.org|ngrok\.io|burpcollaborator|requestbin|"
    r"hookbin|pipedream|webhook\.site|\.onion|tor2web|\.i2p)", re.IGNORECASE,
)

_C2_PORTS = {4444, 4445, 1337, 31337, 6666, 6667, 8888, 9999, 12345}


def scan(
    output: str,
    fs_diff: Optional[dict] = None,
    proxy_requests: Optional[list] = None,
    source_path: Optional[str] = None,
) -> list:
    found = []

    for pat, sev, title in _OUTPUT_PATTERNS:
        m = pat.findall(output)
        if m:
            found.append(Indicator(sev, "process", title, f"Matched: {m[0]!r}"))

    env_m = _ENV_RE.findall(output)
    if env_m:
        found.append(Indicator("high","env","Sensitive env var access",f"Accessed: {', '.join(set(env_m))}"))

    if fs_diff:
        added    = fs_diff.get("added", {})
        modified = fs_diff.get("modified", {})
        removed  = fs_diff.get("removed", {})
        for path_str in {**added, **modified}:
            p = Path(path_str)
            if source_path and not path_str.startswith(source_path):
                found.append(Indicator("high","filesystem","File written outside source dir",path_str))
            for pat in _SENSITIVE_PATHS:
                if pat.search(path_str):
                    found.append(Indicator("critical","filesystem","Write to sensitive path",path_str))
                    break
            if _SUSPICIOUS_EXEC.search(p.name):
                found.append(Indicator("high","filesystem","Suspicious file name created",path_str))
        if len(removed) > 20:
            found.append(Indicator("high","filesystem",f"Mass file deletion ({len(removed)} files)","Possible wiper/ransomware"))

    if proxy_requests:
        blocked = [r for r in proxy_requests if r.get("blocked")]
        if blocked:
            hosts = {r.get("host","?") for r in blocked}
            found.append(Indicator("medium","network",f"Blocked outbound ({len(blocked)})",
                                   f"Attempted: {', '.join(list(hosts)[:5])}"))
        for r in proxy_requests:
            host = r.get("host","")
            url  = r.get("url","")
            if _SUSPICIOUS_HOSTS.search(host):
                found.append(Indicator("critical","network","Connection to suspicious host",
                                       f"{r.get('method','?')} {url}"))
            pm = re.search(r":(\d+)(/|$)", url)
            if pm and int(pm.group(1)) in _C2_PORTS:
                found.append(Indicator("high","network",f"Suspicious port {pm.group(1)}",url))
        unique = {r.get("host") for r in proxy_requests}
        if len(unique) > 30:
            found.append(Indicator("medium","network",f"High unique hosts ({len(unique)})","Possible exfil/beacon"))

    return found


def score(indicators: list) -> int:
    return min(sum(_SEV_SCORE.get(i.severity, 0) for i in indicators), 100)


def print_indicators(indicators: list, proxy_summary: Optional[dict] = None) -> None:
    risk = score(indicators)
    color = "green" if risk < 20 else ("yellow" if risk < 50 else ("red" if risk < 80 else "bold red"))
    console.print(f"\n[bold]Risk score:[/bold] [{color}]{risk}/100[/{color}]")

    if indicators:
        table = Table(title="Suspicious Indicators", show_header=True,
                      header_style="bold dim", box=None, padding=(0,2))
        table.add_column("sev",      no_wrap=True)
        table.add_column("category", style="dim", no_wrap=True)
        table.add_column("indicator")
        table.add_column("detail",   style="dim")
        for ind in sorted(indicators, key=lambda x: -_SEV_SCORE.get(x.severity,0)):
            c = _SEV_COLOR.get(ind.severity,"white")
            table.add_row(f"[{c}]{ind.severity}[/{c}]", ind.category,
                          ind.title, ind.detail[:80])
        console.print(table)
    else:
        console.print("[bold green]✓ No suspicious indicators detected.[/bold green]")

    if proxy_summary:
        console.print(f"\n[bold]Network activity:[/bold]")
        console.print(f"  Total   : {proxy_summary.get('total',0)}")
        console.print(f"  Blocked : [red]{proxy_summary.get('blocked_count',0)}[/red]")
        console.print(f"  Allowed : [green]{proxy_summary.get('allowed_count',0)}[/green]")
        console.print(f"  Hosts   : {proxy_summary.get('unique_hosts',0)}")
        for host, cnt in (proxy_summary.get("top_hosts",[]))[:5]:
            console.print(f"    [cyan]{host}[/cyan]  [dim]{cnt}[/dim]")
    console.print()
