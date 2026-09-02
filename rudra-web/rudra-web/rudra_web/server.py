"""Lightweight zero-dependency HTTP server for Rudra Web Dashboard."""

from __future__ import annotations

import json
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional

from rudra_web.api import (
    get_logs,
    get_rudra_commands,
    get_security_overview,
    get_system_stats,
    list_lab_environments,
    list_osint_reports,
    list_system_services,
)
from rudra_web.html import DASHBOARD_HTML


class RudraHTTPHandler(BaseHTTPRequestHandler):
    def _send_json(self, data: dict | list, code: int = 200) -> None:
        raw = json.dumps(data).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(raw)

    def _send_html(self, html_str: str) -> None:
        raw = html_str.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            self._send_html(DASHBOARD_HTML)
        elif path == "/api/system/status":
            self._send_json(get_system_stats())
        elif path == "/api/services":
            self._send_json(list_system_services())
        elif path == "/api/security":
            self._send_json(get_security_overview())
        elif path == "/api/lab":
            self._send_json(list_lab_environments())
        elif path == "/api/osint":
            self._send_json(list_osint_reports())
        elif path == "/api/commands":
            self._send_json(get_rudra_commands())
        elif path == "/api/logs":
            self._send_json(get_logs())
        else:
            self._send_json({"error": "Not Found"}, code=404)

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/system/optimize":
            try:
                from rudra.system.optimize import optimize_journal_logs, optimize_memory, optimize_package_caches, optimize_ssd_trim, optimize_user_caches
                optimize_package_caches()
                optimize_user_caches()
                optimize_journal_logs()
                optimize_memory()
                optimize_ssd_trim()
                self._send_json({"status": "success", "message": "Optimization executed"})
            except Exception as e:
                self._send_json({"status": "error", "message": str(e)}, code=500)
        else:
            self._send_json({"error": "Not Found"}, code=404)

    def log_message(self, format, *args):
        # Silent standard logging to keep terminal clean
        pass


def run_dashboard_server(host: str = "127.0.0.1", port: int = 8080) -> HTTPServer:
    """Start and return the HTTP server instance."""
    server = HTTPServer((host, port), RudraHTTPHandler)
    return server
