"""Generate isolation run reports — markdown, json, html, terminal."""

from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from rich.console import Console

console = Console()

_SEV_SCORE = {"critical":100,"high":40,"medium":15,"low":5,"info":1}


def _score(indicators: list) -> int:
    return min(sum(_SEV_SCORE.get(i.severity,0) for i in indicators), 100)


class RunReport:
    def __init__(self, lab_name, command, exit_code, output, tier,
                 source_path, internet_mode, indicators, proxy_summary,
                 fs_diff, duration_s, cfg=None):
        self.lab_name      = lab_name
        self.command       = command
        self.exit_code     = exit_code
        self.output        = output
        self.tier          = tier
        self.source_path   = source_path
        self.internet_mode = internet_mode
        self.indicators    = indicators or []
        self.proxy_summary = proxy_summary or {}
        self.fs_diff       = fs_diff or {}
        self.duration_s    = duration_s
        self.cfg           = cfg
        self.timestamp     = datetime.now().isoformat()
        self.risk_score    = _score(self.indicators)

    def to_markdown(self) -> str:
        lines = [
            "# rudra lab isolate — Run Report\n",
            f"| Field | Value |",
            f"|---|---|",
            f"| Lab | `{self.lab_name}` |",
            f"| Command | `{self.command}` |",
            f"| Exit code | `{self.exit_code}` |",
            f"| Tier | `{self.tier}` |",
            f"| Internet | `{self.internet_mode}` |",
            f"| Source | `{self.source_path}` |",
            f"| Duration | {self.duration_s:.1f}s |",
            f"| Timestamp | {self.timestamp} |",
            f"| **Risk score** | **{self.risk_score}/100** |",
            "",
            "## Suspicious Indicators",
        ]
        if self.indicators:
            lines += ["", "| Severity | Category | Indicator | Detail |", "|---|---|---|---|"]
            for ind in sorted(self.indicators, key=lambda x: -_SEV_SCORE.get(x.severity,0)):
                lines.append(f"| {ind.severity} | {ind.category} | {ind.title} | {ind.detail[:80]} |")
        else:
            lines.append("\n✅ No suspicious indicators detected.")

        if self.proxy_summary:
            lines += ["", "## Network Activity", "",
                f"- Total: {self.proxy_summary.get('total',0)}",
                f"- Blocked: {self.proxy_summary.get('blocked_count',0)}",
                f"- Allowed: {self.proxy_summary.get('allowed_count',0)}",
                f"- Unique hosts: {self.proxy_summary.get('unique_hosts',0)}"]
            top = self.proxy_summary.get("top_hosts",[])
            if top:
                lines += ["", "### Top Hosts","","| Host | Requests |","|---|---|"]
                for h,c in top:
                    lines.append(f"| `{h}` | {c} |")
            bh = self.proxy_summary.get("blocked_hosts",[])
            if bh:
                lines += ["", "### Blocked Hosts",""]
                lines += [f"- `{h}`" for h in bh]

        if self.fs_diff:
            lines += ["", "## File System Changes",""]
            for ctype in ("added","modified","removed"):
                items = self.fs_diff.get(ctype,{})
                if items:
                    lines += [f"### {ctype.title()} ({len(items)})",""]
                    lines += [f"- `{p}`" for p in list(items)[:50]]
                    if len(items) > 50:
                        lines.append(f"- _...and {len(items)-50} more_")

        lines += ["","## Command Output","","```",
                  self.output[:8000] + ("..." if len(self.output)>8000 else ""),
                  "```",""]
        return "\n".join(lines)

    def to_json(self) -> str:
        return json.dumps({
            "lab_name": self.lab_name, "command": self.command,
            "exit_code": self.exit_code, "tier": self.tier,
            "internet_mode": self.internet_mode, "source_path": self.source_path,
            "duration_s": self.duration_s, "timestamp": self.timestamp,
            "risk_score": self.risk_score,
            "indicators": [{"severity":i.severity,"category":i.category,
                            "title":i.title,"detail":i.detail} for i in self.indicators],
            "proxy_summary": self.proxy_summary,
            "fs_diff": self.fs_diff,
            "output": self.output[:20000],
        }, indent=2)

    def to_html(self) -> str:
        risk  = self.risk_score
        rc    = "#22c55e" if risk<20 else ("#eab308" if risk<50 else ("#ef4444" if risk<80 else "#7f1d1d"))
        sc    = {"critical":"#7f1d1d","high":"#ef4444","medium":"#eab308","low":"#a3a3a3","info":"#737373"}
        irows = "".join(
            f'<tr><td style="color:{sc.get(i.severity,"#fff")};font-weight:bold">{i.severity}</td>'
            f'<td>{i.category}</td><td>{i.title}</td><td style="color:#a3a3a3">{i.detail[:80]}</td></tr>'
            for i in sorted(self.indicators, key=lambda x: -_SEV_SCORE.get(x.severity,0))
        )
        net = ""
        if self.proxy_summary:
            top_rows = "".join(f"<tr><td><code>{h}</code></td><td>{c}</td></tr>"
                               for h,c in self.proxy_summary.get("top_hosts",[]))
            net = (f'<h2>Network Activity</h2><p>'
                   f'Total:{self.proxy_summary.get("total",0)} &nbsp;'
                   f'Blocked:<span style="color:#ef4444">{self.proxy_summary.get("blocked_count",0)}</span> &nbsp;'
                   f'Allowed:<span style="color:#22c55e">{self.proxy_summary.get("allowed_count",0)}</span></p>'
                   f'<table><tr><th>Host</th><th>Reqs</th></tr>{top_rows}</table>')
        fs = ""
        for ct in ("added","modified","removed"):
            items = self.fs_diff.get(ct,{})
            if items:
                col = {"added":"#22c55e","modified":"#eab308","removed":"#ef4444"}.get(ct,"#fff")
                rows = "".join(f"<li><code>{p}</code></li>" for p in list(items)[:30])
                fs += f'<h3 style="color:{col}">{ct.title()} ({len(items)})</h3><ul>{rows}</ul>'
        out_esc = self.output[:10000].replace("<","&lt;").replace(">","&gt;")
        ind_section = (f'<table><tr><th>Sev</th><th>Cat</th><th>Indicator</th><th>Detail</th></tr>{irows}</table>'
                       if self.indicators else '<p style="color:#22c55e">✅ No indicators.</p>')
        return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<title>rudra lab — {self.lab_name}</title>
<style>
body{{background:#0f0f0f;color:#e5e5e5;font-family:monospace;max-width:1000px;margin:2rem auto;padding:1rem}}
h1{{color:#06b6d4}}h2{{color:#a3e635;border-bottom:1px solid #333;padding-bottom:.3rem}}
table{{border-collapse:collapse;width:100%;margin:1rem 0}}
th{{background:#1a1a1a;color:#a3a3a3;padding:.4rem .8rem;text-align:left}}
td{{padding:.3rem .8rem;border-bottom:1px solid #1f1f1f}}
code{{background:#1a1a1a;padding:.1rem .3rem;border-radius:3px;color:#06b6d4}}
pre{{background:#1a1a1a;padding:1rem;overflow-x:auto;border-radius:6px;color:#a3e635}}
.risk{{font-size:2rem;font-weight:bold;color:{rc}}}
</style></head><body>
<h1>🔬 rudra lab isolate — Report</h1>
<p class="risk">Risk: {risk}/100</p>
<table>
<tr><td><b>Lab</b></td><td><code>{self.lab_name}</code></td></tr>
<tr><td><b>Command</b></td><td><code>{self.command}</code></td></tr>
<tr><td><b>Exit code</b></td><td><code>{self.exit_code}</code></td></tr>
<tr><td><b>Tier</b></td><td><code>{self.tier}</code></td></tr>
<tr><td><b>Internet</b></td><td><code>{self.internet_mode}</code></td></tr>
<tr><td><b>Duration</b></td><td>{self.duration_s:.1f}s</td></tr>
<tr><td><b>Timestamp</b></td><td>{self.timestamp}</td></tr>
</table>
<h2>Suspicious Indicators</h2>{ind_section}
{net}
<h2>File System Changes</h2>{fs if fs else '<p style="color:#a3a3a3">No changes recorded.</p>'}
<h2>Command Output</h2><pre>{out_esc}</pre>
</body></html>"""

    def save(self, formats: list, name_hint: str = "") -> dict:
        from rudra_lab.helpers import LAB_DIR
        reports_dir = LAB_DIR / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = self.lab_name + (f"_{name_hint}" if name_hint else "") + f"_{ts}"
        saved = {}
        if "md" in formats or "markdown" in formats:
            p = reports_dir / f"{base}.md";  p.write_text(self.to_markdown()); saved["md"] = p
        if "json" in formats:
            p = reports_dir / f"{base}.json"; p.write_text(self.to_json());    saved["json"] = p
        if "html" in formats:
            p = reports_dir / f"{base}.html"; p.write_text(self.to_html());    saved["html"] = p
        return saved
