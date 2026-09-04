"""Terminal QR code generator for rudra-share."""

from __future__ import annotations

import urllib.request
import urllib.error


def render_terminal_qr(url: str, timeout: int = 4) -> str | None:
    """Generate ANSI block QR code string for display in terminal."""
    # 1. Try local qrcode package if installed
    try:
        import io
        import qrcode
        qr = qrcode.QRCode()
        qr.add_data(url)
        qr.make(fit=True)
        f = io.StringIO()
        qr.print_ascii(out=f, invert=True)
        f.seek(0)
        return f.read()
    except Exception:
        pass

    # 2. Try qrenco.de online generator
    try:
        req = urllib.request.Request(
            f"https://qrenco.de/{url}",
            headers={"User-Agent": "curl/7.88.1"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception:
        return None
