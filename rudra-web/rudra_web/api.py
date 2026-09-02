"""REST API handlers powering the Rudra Web Dashboard."""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from rudra.pkgmanagers import available_backends
from rudra.shell import capture, have


def get_system_stats() -> dict[str, Any]:
    """Collect CPU, RAM, Disk, and Host details."""
    # 1. RAM info from /proc/meminfo
    mem_total, mem_avail, mem_used = 0, 0, 0
    try:
        with open("/proc/meminfo") as f:
            lines = f.readlines()
        mem = {}
        for l in lines:
            parts = l.split(":")
            if len(parts) == 2:
                mem[parts[0].strip()] = int(parts[1].strip().split()[0])
        mem_total = mem.get("MemTotal", 0) // 1024
        mem_avail = mem.get("MemAvailable", mem.get("MemFree", 0)) // 1024
        mem_used = max(0, mem_total - mem_avail)
    except Exception:
        pass

    # 2. Disk usage
    disk_total, disk_used, disk_free, disk_pct = 0, 0, 0, 0
    try:
        st = os.statvfs("/")
        disk_total = (st.f_blocks * st.f_frsize) // (1024 * 1024 * 1024)
        disk_free = (st.f_bavail * st.f_frsize) // (1024 * 1024 * 1024)
        disk_used = max(0, disk_total - disk_free)
        disk_pct = int((disk_used / disk_total) * 100) if disk_total else 0
    except Exception:
        pass

    # 3. CPU Load & Uptime
    load_avg = [0.0, 0.0, 0.0]
    uptime_str = ""
    try:
        load_avg = [round(x, 2) for x in os.getloadavg()]
        with open("/proc/uptime") as f:
            up_secs = int(float(f.readline().split()[0]))
            hours, rem = divmod(up_secs, 3600)
            mins, _ = divmod(rem, 60)
            uptime_str = f"{hours}h {mins}m"
    except Exception:
        pass

    # 4. OS details
    os_name = platform.system()
    kernel = platform.release()
    hostname = platform.node()

    return {
        "hostname": hostname,
        "os": os_name,
        "kernel": kernel,
        "uptime": uptime_str,
        "cpu_load": load_avg,
        "cpu_count": os.cpu_count() or 1,
        "ram": {
            "total_mb": mem_total,
            "used_mb": mem_used,
            "available_mb": mem_avail,
            "pct": int((mem_used / mem_total) * 100) if mem_total else 0,
        },
        "disk": {
            "total_gb": disk_total,
            "used_gb": disk_used,
            "free_gb": disk_free,
            "pct": disk_pct,
        },
        "backends": list(available_backends(probe=False).keys()),
    }


def list_system_services(limit: int = 50) -> list[dict[str, Any]]:
    """List systemd services."""
    services = []
    if not have("systemctl"):
        return []

    code, out = capture(["systemctl", "list-units", "--type=service", "--no-pager", "--no-legend", "--all"])
    if code == 0:
        for line in out.splitlines()[:limit]:
            parts = line.split(None, 4)
            if len(parts) >= 4:
                unit = parts[0]
                load_state = parts[1]
                active_state = parts[2]
                sub_state = parts[3]
                desc = parts[4] if len(parts) > 4 else ""
                services.append({
                    "unit": unit,
                    "active": active_state == "active",
                    "state": f"{active_state} ({sub_state})",
                    "desc": desc,
                })
    return services


def get_security_overview() -> dict[str, Any]:
    """Collect firewall, fail2ban, and scan summary without requiring sudo password."""
    firewall_status = "inactive"
    if have("ufw"):
        code, out = capture(["systemctl", "is-active", "ufw"])
        firewall_status = "active (ufw)" if out.strip() == "active" else "inactive (ufw)"
    elif have("firewall-cmd"):
        code, out = capture(["systemctl", "is-active", "firewalld"])
        firewall_status = "active (firewalld)" if out.strip() == "active" else "inactive (firewalld)"
    elif have("iptables"):
        firewall_status = "available (iptables)"

    f2b_status = "not installed"
    banned_count = 0
    if have("fail2ban-client"):
        code, out = capture(["systemctl", "is-active", "fail2ban"])
        f2b_status = "active" if out.strip() == "active" else "inactive"

    apparmor_status = "inactive"
    if have("aa-status"):
        code, out = capture(["systemctl", "is-active", "apparmor"])
        apparmor_status = "active" if out.strip() == "active" else "inactive"

    return {
        "firewall": firewall_status,
        "fail2ban": f2b_status,
        "fail2ban_banned": banned_count,
        "apparmor": apparmor_status,
    }


def list_lab_environments() -> list[dict[str, Any]]:
    """List Rudra Lab environments."""
    labs_dir = Path.home() / ".rudra" / "lab" / "labs"
    labs = []
    if labs_dir.is_dir():
        for d in labs_dir.iterdir():
            if d.is_dir():
                meta_file = d / "meta.json"
                meta = {}
                if meta_file.exists():
                    try:
                        meta = json.loads(meta_file.read_text())
                    except Exception:
                        pass
                labs.append({
                    "name": d.name,
                    "path": str(d),
                    "created_at": meta.get("created_at", "unknown"),
                    "tier": meta.get("tier", "unshare"),
                })
    return labs


def list_osint_reports() -> list[dict[str, Any]]:
    """List saved OSINT investigation dossiers."""
    reports_dir = Path.home() / ".rudra" / "osint" / "reports"
    reports = []
    if reports_dir.is_dir():
        for f in sorted(reports_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:30]:
            size_kb = round(f.stat().st_size / 1024, 1)
            mtime = time.strftime("%Y-%m-%d %H:%M", time.localtime(f.stat().st_mtime))
            reports.append({
                "filename": f.name,
                "path": str(f),
                "size_kb": size_kb,
                "modified": mtime,
                "preview": f.read_text(encoding="utf-8", errors="replace")[:1000],
            })
    return reports


RUDRA_COMMANDS: list[dict[str, Any]] = [
    # ── Core ────────────────────────────────────────────────────────────────────
    {"category": "Core", "cmd": "rudra --help",             "desc": "Show all top-level commands and global options"},
    {"category": "Core", "cmd": "rudra version",            "desc": "Display the installed Rudra version"},
    {"category": "Core", "cmd": "rudra self-upgrade",       "desc": "Upgrade Rudra itself to the latest version from GitHub"},
    {"category": "Core", "cmd": "rudra plugin list",        "desc": "List all installed plugins with status"},
    {"category": "Core", "cmd": "rudra plugin info <name>", "desc": "Show detailed info about a specific plugin"},

    # ── Package Managers — Discovery ─────────────────────────────────────────────
    {"category": "Packages — Discovery", "cmd": "rudra managers",               "desc": "Show all detected package managers and their supported operations"},
    {"category": "Packages — Discovery", "cmd": "rudra managers --kind system",  "desc": "Filter to system package managers only (pacman, apt, dnf …)"},
    {"category": "Packages — Discovery", "cmd": "rudra managers --kind aur",     "desc": "Filter to AUR helpers (yay, paru)"},
    {"category": "Packages — Discovery", "cmd": "rudra managers --kind universal","desc": "Filter to universal managers (flatpak, snap, nix)"},
    {"category": "Packages — Discovery", "cmd": "rudra managers --kind language", "desc": "Filter to language managers (pip, cargo, gem, npm)"},
    {"category": "Packages — Discovery", "cmd": "rudra managers --no-probe",     "desc": "Skip PATH scan for unknown managers (faster)"},

    # ── Package Managers — Install ───────────────────────────────────────────────
    {"category": "Packages — Install", "cmd": "rudra install <pkg>",                    "desc": "Smart install — Rudra picks the best backend (PyPI/crates.io/flatpak heuristics)"},
    {"category": "Packages — Install", "cmd": "rudra install <pkg> --with paru",        "desc": "Force install via a specific backend (paru, apt, dnf, flatpak, pip …)"},
    {"category": "Packages — Install", "cmd": "rudra install <pkg> --no-smart",         "desc": "Skip smart detection, fall back to system package manager"},
    {"category": "Packages — Install", "cmd": "rudra install <pkg> --theme rpg",        "desc": "Install with a progress bar theme (rpg, silly, sarcastic, dramatic, default)"},
    {"category": "Packages — Install", "cmd": "rudra install --set-theme rpg",          "desc": "Persist a progress theme as your default (~/.rudra/config.toml)"},
    {"category": "Packages — Install", "cmd": "rudra install <pkg1> <pkg2>",            "desc": "Install multiple packages in one command"},
    {"category": "Packages — Install", "cmd": "rudra install",                          "desc": "Show available progress bar themes"},

    # ── Package Managers — Remove ────────────────────────────────────────────────
    {"category": "Packages — Remove", "cmd": "rudra remove <pkg>",              "desc": "Remove a package (system + AUR by default)"},
    {"category": "Packages — Remove", "cmd": "rudra remove <pkg> --with apt",   "desc": "Remove via a specific backend"},
    {"category": "Packages — Remove", "cmd": "rudra autoremove",                "desc": "Remove orphaned/unused packages (auto-detects pacman orphans via pacman -Qtdq)"},
    {"category": "Packages — Remove", "cmd": "rudra autoremove --with zypper",  "desc": "List orphans on zypper (manual removal required — zypper limitation)"},

    # ── Package Managers — Update & Upgrade ──────────────────────────────────────
    {"category": "Packages — Update & Upgrade", "cmd": "rudra update",                              "desc": "Refresh all system + AUR package databases"},
    {"category": "Packages — Update & Upgrade", "cmd": "rudra update --with apt",                   "desc": "Refresh a specific backend's database only"},
    {"category": "Packages — Update & Upgrade", "cmd": "rudra upgrade",                             "desc": "Upgrade all packages (syncs DB first)"},
    {"category": "Packages — Update & Upgrade", "cmd": "rudra upgrade --with paru",                 "desc": "Upgrade via a specific backend only"},
    {"category": "Packages — Update & Upgrade", "cmd": "rudra full-upgrade",                        "desc": "Upgrade system + AUR + flatpak/snap/nix (everything universal)"},
    {"category": "Packages — Update & Upgrade", "cmd": "rudra full-upgrade --language",             "desc": "Also upgrade language packages: pip, cargo, gem, npm -g"},
    {"category": "Packages — Update & Upgrade", "cmd": "rudra full-upgrade --no-universal",         "desc": "Full upgrade but skip flatpak/snap/nix"},
    {"category": "Packages — Update & Upgrade", "cmd": "rudra system check",                        "desc": "List available updates without installing anything"},
    {"category": "Packages — Update & Upgrade", "cmd": "rudra system check --universal",            "desc": "Also check flatpak/snap/nix for updates"},
    {"category": "Packages — Update & Upgrade", "cmd": "rudra system check --language",             "desc": "Also check pip/cargo/gem for outdated packages"},

    # ── Package Managers — Search & Info ─────────────────────────────────────────
    {"category": "Packages — Search & Info", "cmd": "rudra search <query>",              "desc": "Search for a package (system + AUR by default)"},
    {"category": "Packages — Search & Info", "cmd": "rudra search <query> --all",        "desc": "Search across all backends: system, flatpak, snap, pip, npm …"},
    {"category": "Packages — Search & Info", "cmd": "rudra search <query> --with pip",   "desc": "Search only on a specific backend"},
    {"category": "Packages — Search & Info", "cmd": "rudra system info <pkg>",           "desc": "Show detailed info about an installed or available package"},
    {"category": "Packages — Search & Info", "cmd": "rudra system info <pkg> --with dnf","desc": "Query info from a specific backend"},
    {"category": "Packages — Search & Info", "cmd": "rudra system list",                 "desc": "List all installed packages (system + AUR)"},
    {"category": "Packages — Search & Info", "cmd": "rudra system list <filter>",        "desc": "List installed packages matching a search term"},
    {"category": "Packages — Search & Info", "cmd": "rudra system list --universal",     "desc": "Also list flatpak/snap/nix installed apps"},
    {"category": "Packages — Search & Info", "cmd": "rudra system list --language",      "desc": "Also list pip/cargo/gem/npm global packages"},
    {"category": "Packages — Search & Info", "cmd": "rudra system owns /usr/bin/ffmpeg", "desc": "Find which package owns a given file path"},

    # ── Self-Healing Engine ───────────────────────────────────────────────────────
    {"category": "Self-Healing", "cmd": "rudra heal doctor",                       "desc": "Audit all detected package managers and tools against syntax health"},
    {"category": "Self-Healing", "cmd": "rudra heal system",                       "desc": "Diagnose & auto-repair stale package locks, keyrings & interrupted tasks"},
    {"category": "Self-Healing", "cmd": "rudra heal run \"<command>\"",           "desc": "Execute any command and automatically heal if syntax/flags fail"},
    {"category": "Self-Healing", "cmd": "rudra heal show",                          "desc": "Show all cached and pinned syntax fixes Rudra has learned"},
    {"category": "Self-Healing", "cmd": "rudra heal pin <tool> <op> \"<cmd>\"",   "desc": "Manually pin a corrected command for a tool+operation"},
    {"category": "Self-Healing", "cmd": "rudra heal clear",                        "desc": "Clear all cached syntax fixes"},

    # ── Theme Engine (plugin) ─────────────────────────────────────────────────────
    {"category": "Theme (plugin)", "cmd": "rudra theme list",                      "desc": "List all 10 available themes with color swatch palettes"},
    {"category": "Theme (plugin)", "cmd": "rudra theme preview <name>",            "desc": "Live preview banners, panels, tables, and swatches for a theme"},
    {"category": "Theme (plugin)", "cmd": "rudra theme set <name>",                "desc": "Activate a theme globally (cyberpunk, dracula, catppuccin, nord …)"},
    {"category": "Theme (plugin)", "cmd": "rudra theme current",                   "desc": "Show currently active theme"},
    {"category": "Theme (plugin)", "cmd": "rudra theme install <url-or-file>",     "desc": "Download and install an individual standalone theme without whole bundles"},
    {"category": "Theme (plugin)", "cmd": "rudra theme export <name>",             "desc": "Export a custom theme definition to JSON"},
    {"category": "Theme (plugin)", "cmd": "rudra theme reset",                     "desc": "Reset theme to Rudra Classic default"},

    # ── Optimize ──────────────────────────────────────────────────────────────────
    {"category": "Optimize", "cmd": "rudra optimize",            "desc": "Run full system optimization (caches, journals, TRIM, RAM)"},
    {"category": "Optimize", "cmd": "rudra optimize --dry-run",  "desc": "Preview what optimize would do without making changes"},

    # ── Security ──────────────────────────────────────────────────────────────────
    {"category": "Security", "cmd": "rudra security status",              "desc": "Overall security posture overview"},
    {"category": "Security", "cmd": "rudra security firewall status",     "desc": "Show firewall rules and active status"},
    {"category": "Security", "cmd": "rudra security firewall enable",     "desc": "Enable the system firewall (UFW/firewalld)"},
    {"category": "Security", "cmd": "rudra security firewall disable",    "desc": "Disable the system firewall"},
    {"category": "Security", "cmd": "rudra security fail2ban status",     "desc": "Show fail2ban jail status and banned IPs"},
    {"category": "Security", "cmd": "rudra security audit",               "desc": "Run a Lynis security audit scan"},
    {"category": "Security", "cmd": "rudra security virus-scan <path>",   "desc": "Scan a path with ClamAV antivirus"},
    {"category": "Security", "cmd": "rudra security apparmor status",     "desc": "Show AppArmor MAC status"},

    # ── Project & Task Management ─────────────────────────────────────────────────
    {"category": "Project & Tasks", "cmd": "rudra project dashboard",                      "desc": "Morning briefing: overdue tasks, in-progress items, active timer & metrics"},
    {"category": "Project & Tasks", "cmd": "rudra project board",                          "desc": "Interactive 3-column Kanban board (Todo → In Progress → Done)"},
    {"category": "Project & Tasks", "cmd": "rudra project list",                           "desc": "List all tracked projects with health icons, language badges & task counts"},
    {"category": "Project & Tasks", "cmd": "rudra project list --sort activity",          "desc": "Sort projects by most recently opened / worked on"},
    {"category": "Project & Tasks", "cmd": "rudra project add-task <p> \"<task>\" -p high","desc": "Add a task with priority (low/medium/high) and due date"},
    {"category": "Project & Tasks", "cmd": "rudra project tasks --all-projects",           "desc": "View all open tasks across every project in a unified table"},
    {"category": "Project & Tasks", "cmd": "rudra project move-task <p> <id> in-progress", "desc": "Move a task on the Kanban board (todo, in-progress, done)"},
    {"category": "Project & Tasks", "cmd": "rudra project done <p> <id>",                  "desc": "Mark a task as completed"},
    {"category": "Project & Tasks", "cmd": "rudra project log start <p> -n \"task\"",       "desc": "Start a live work session timer on a project"},
    {"category": "Project & Tasks", "cmd": "rudra project log stop",                       "desc": "Stop active timer and record session duration"},
    {"category": "Project & Tasks", "cmd": "rudra project sprint new <p> <name> -d +14d",  "desc": "Create a sprint milestone with a deadline"},
    {"category": "Project & Tasks", "cmd": "rudra project sprint status <p>",              "desc": "Sprint progress bar and completed task percentage"},
    {"category": "Project & Tasks", "cmd": "rudra project activity [p]",                   "desc": "Chronological audit feed of project edits, tasks & timer events"},
    {"category": "Project & Tasks", "cmd": "rudra project open <p>",                       "desc": "Fuzzy-search and open a project subshell with mini-briefing"},
    {"category": "Project & Tasks", "cmd": "rudra project open <p> -e code",               "desc": "Open project folder directly in an editor (code, nvim, zed)"},

    # ── Archive ───────────────────────────────────────────────────────────────────
    {"category": "Archive", "cmd": "rudra archive extract <file>",        "desc": "Extract any archive (zip, tar, 7z, rar …)"},
    {"category": "Archive", "cmd": "rudra extract <file>",                "desc": "Shortcut alias for archive extract"},
    {"category": "Archive", "cmd": "rudra archive create <out> <files>",  "desc": "Create a new archive from files/directories"},
    {"category": "Archive", "cmd": "rudra archive list <file>",           "desc": "Peek inside an archive without extracting"},

    # ── Recon ─────────────────────────────────────────────────────────────────────
    {"category": "Recon", "cmd": "rudra recon <host>",            "desc": "All-in-one recon: nmap, whois, traceroute, DNS, HTTP, TLS"},
    {"category": "Recon", "cmd": "rudra recon-tools ports <ip>",  "desc": "Port scan with nmap"},
    {"category": "Recon", "cmd": "rudra recon-tools whois <host>","desc": "WHOIS domain / IP lookup"},
    {"category": "Recon", "cmd": "rudra recon-tools dns <host>",  "desc": "DNS resolution and records"},
    {"category": "Recon", "cmd": "rudra recon-tools http <url>",  "desc": "HTTP headers and response info"},
    {"category": "Recon", "cmd": "rudra recon-tools tls <host>",  "desc": "TLS certificate details and chain"},
    {"category": "Recon", "cmd": "rudra recon-tools ping <host>", "desc": "Ping / ICMP latency check"},
    {"category": "Recon", "cmd": "rudra recon-tools traceroute <host>","desc": "Network path traceroute"},

    # ── Git (plugin) ──────────────────────────────────────────────────────────────
    {"category": "Git (plugin)", "cmd": "rudra git status",         "desc": "Pretty git status with branch and diff summary"},
    {"category": "Git (plugin)", "cmd": "rudra git log",            "desc": "Visual commit history graph"},
    {"category": "Git (plugin)", "cmd": "rudra git sync",           "desc": "Pull + push in one command"},
    {"category": "Git (plugin)", "cmd": "rudra git undo",           "desc": "Undo last commit (keep changes staged)"},
    {"category": "Git (plugin)", "cmd": "rudra git stash",          "desc": "Stash uncommitted changes"},
    {"category": "Git (plugin)", "cmd": "rudra git branch <name>",  "desc": "Create and switch to a new branch"},

    # ── Lab (plugin) ──────────────────────────────────────────────────────────────
    {"category": "Lab (plugin)", "cmd": "rudra lab create <name>",          "desc": "Spawn a new disposable isolated sandbox environment"},
    {"category": "Lab (plugin)", "cmd": "rudra lab list",                   "desc": "List all lab environments"},
    {"category": "Lab (plugin)", "cmd": "rudra lab enter <name>",           "desc": "Enter / shell into an existing lab"},
    {"category": "Lab (plugin)", "cmd": "rudra lab destroy <name>",         "desc": "Destroy and wipe a lab environment"},
    {"category": "Lab (plugin)", "cmd": "rudra lab create <name> --proxy",  "desc": "Spawn a lab with mitmproxy traffic capture"},

    # ── OSINT (plugin) ────────────────────────────────────────────────────────────
    {"category": "OSINT (plugin)", "cmd": "rudra osint <target> --basic",      "desc": "Surface-level passive recon — safe, no active probing"},
    {"category": "OSINT (plugin)", "cmd": "rudra osint <target> --legal-deep", "desc": "Deep passive recon — CT logs, Wayback, 60+ platforms, GPS"},
    {"category": "OSINT (plugin)", "cmd": "rudra osint <target> --deep",       "desc": "Full active recon with disclaimer (requires confirmation)"},
    {"category": "OSINT (plugin)", "cmd": "rudra osint reports",               "desc": "List saved OSINT investigation dossiers"},

    # ── Web UI (plugin) ───────────────────────────────────────────────────────────
    {"category": "Web UI (plugin)", "cmd": "rudra web",                    "desc": "Start the web dashboard in the background"},
    {"category": "Web UI (plugin)", "cmd": "rudra web stop",               "desc": "Stop the background web dashboard server"},
    {"category": "Web UI (plugin)", "cmd": "rudra web status",             "desc": "Show if the dashboard is running and its PID"},
    {"category": "Web UI (plugin)", "cmd": "rudra web logs",               "desc": "Show the web dashboard server logs"},
    {"category": "Web UI (plugin)", "cmd": "rudra web logs --follow",      "desc": "Stream live dashboard server logs"},
    {"category": "Web UI (plugin)", "cmd": "rudra web start --port 9090",  "desc": "Start the dashboard on a custom port"},
    {"category": "Web UI (plugin)", "cmd": "rudra web start --fg",         "desc": "Start the dashboard in foreground (blocks terminal)"},
]


def get_rudra_commands() -> list[dict[str, Any]]:
    """Return the full organized Rudra command reference catalog."""
    return RUDRA_COMMANDS


def get_logs() -> dict[str, Any]:
    """Return Rudra web server log and recent system journal warnings."""
    log_file = Path.home() / ".rudra" / "web" / "rudra-web.log"
    web_log = ""
    if log_file.exists():
        try:
            lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
            web_log = "\n".join(lines[-300:])
        except Exception:
            web_log = "(could not read log)"
    else:
        web_log = "(no log file yet — server hasn't written any entries)"

    journal_log = ""
    if have("journalctl"):
        code, out = capture([
            "journalctl", "--no-pager", "-n", "150",
            "--output=short-iso", "--priority=warning",
        ])
        journal_log = out.strip() if code == 0 else "(journalctl unavailable)"

    return {
        "web_server": web_log,
        "system_journal": journal_log,
    }
