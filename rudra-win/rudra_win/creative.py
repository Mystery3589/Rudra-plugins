"""rudra-win creative superpowers: toast, speak, matrix, wallpaper, and fun desktop tricks.

All commands are Windows-only and use PowerShell under the hood.
"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel

from rudra_win.core import run_powershell, IS_WINDOWS

console = Console()
app = typer.Typer(help="🎨 Creative & fun Windows desktop superpowers.", no_args_is_help=True)


def _win_only() -> None:
    if not IS_WINDOWS:
        console.print("[bold yellow]⚠ This command is Windows-only. It will have no effect on Linux/macOS.[/bold yellow]")
        console.print("[dim]You can safely run rudra win commands on a Windows machine or inside WSL with a Windows host.[/dim]")


# ── rudra win toast ───────────────────────────────────────────────────────────

@app.command(name="toast")
def toast(
    title: str = typer.Argument(..., help="Notification title text."),
    message: str = typer.Argument("", help="Notification body message."),
    duration: int = typer.Option(5, "--duration", "-d", help="How long the toast stays visible (seconds)."),
):
    """🔔 Fire a native Windows toast notification from the terminal.

    Examples:
      rudra win toast "Build done!" "Tests passed in 4.2s"
      rudra win toast "Server ready" "Listening on :8080"
      rudra win toast "Deploy complete"
    """
    _win_only()
    ps = f"""
$xml = [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType=WindowsRuntime]::new()
$xml.LoadXml('<toast><visual><binding template="ToastText02"><text id="1">{title}</text><text id="2">{message}</text></binding></visual></toast>')
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime] | Out-Null
$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
$toast.ExpirationTime = [DateTimeOffset]::Now.AddSeconds({duration})
$notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Rudra")
$notifier.Show($toast)
"""
    console.print(f"[bold green]🔔 Firing toast:[/bold green] [cyan]{title}[/cyan] — {message}")
    run_powershell(ps)


# ── rudra win speak ───────────────────────────────────────────────────────────

@app.command(name="speak")
def speak(
    text: str = typer.Argument(..., help="Text to speak aloud via Windows TTS."),
    rate: int = typer.Option(0, "--rate", "-r", help="Speech rate: -10 (slowest) to +10 (fastest). 0 = normal."),
):
    """🗣 Speak text aloud using Windows Text-to-Speech engine.

    Examples:
      rudra win speak "Build complete, all tests passing"
      rudra win speak "WARNING: Server is overloaded" --rate -2
      rudra win speak "Hello, I am Rudra"
    """
    _win_only()
    safe = text.replace('"', '\\"').replace("'", "''")
    ps = f"""
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.Rate = {rate}
$synth.Speak('{safe}')
"""
    console.print(f"[bold cyan]🗣 Speaking:[/bold cyan] \"{text}\"")
    run_powershell(ps)


# ── rudra win matrix ──────────────────────────────────────────────────────────

@app.command(name="matrix")
def matrix(
    duration: int = typer.Option(10, "--duration", "-d", help="How many seconds to run the matrix rain."),
):
    """💊 Summon a full-screen green Matrix code rain in the terminal.

    Runs right inside your current terminal window. Press any key to exit early.

    Example:
      rudra win matrix
      rudra win matrix --duration 30
    """
    import time
    import random
    import os
    import sys

    MATRIX_CHARS = "アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホ01アイウエオ10ランダムコード"
    cols = os.get_terminal_size().columns
    rows = os.get_terminal_size().lines - 2

    drops = [random.randint(-rows, 0) for _ in range(cols // 2)]
    deadline = time.time() + duration

    console.print(f"[bold green]💊 Entering the Matrix for {duration}s... (Ctrl+C to exit)[/bold green]\n")
    time.sleep(0.4)

    try:
        # Use ANSI codes directly for speed
        sys.stdout.write("\033[?25l")  # hide cursor
        sys.stdout.write("\033[2J")    # clear screen
        while time.time() < deadline:
            sys.stdout.write("\033[H")  # cursor home
            lines = []
            for row in range(rows):
                line_chars = []
                for col_i, drop in enumerate(drops):
                    if drop == row:
                        ch = random.choice(MATRIX_CHARS)
                        line_chars.append(f"\033[1;32m{ch}\033[0m")  # bright green head
                    elif 0 <= row < drop:
                        ch = random.choice(MATRIX_CHARS)
                        fade = max(0, 255 - (drop - row) * 40)
                        line_chars.append(f"\033[38;2;0;{min(fade,255)};0m{ch}\033[0m")
                    else:
                        line_chars.append(" ")
                    line_chars.append(" ")  # char width spacing
                lines.append("".join(line_chars))
            sys.stdout.write("\n".join(lines))
            sys.stdout.flush()
            for i in range(len(drops)):
                if drops[i] > rows + random.randint(0, 8):
                    drops[i] = random.randint(-rows, 0)
                else:
                    drops[i] += 1
            time.sleep(0.045)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write("\033[?25h")  # show cursor
        sys.stdout.write("\033[0m\033[2J\033[H")  # reset + clear
        sys.stdout.flush()

    console.print("[bold green]You took the green pill. Welcome back.[/bold green]")


# ── rudra win wallpaper ────────────────────────────────────────────────────────

@app.command(name="wallpaper")
def wallpaper(
    path: str = typer.Argument(..., help="Absolute path to the image file to set as wallpaper."),
):
    """🖼  Set desktop wallpaper from any image path via PowerShell.

    Example:
      rudra win wallpaper C:\\\\Users\\\\You\\\\Pictures\\\\bg.jpg
    """
    _win_only()
    ps = f"""
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Wallpaper {{
    [DllImport("user32.dll", CharSet = CharSet.Auto)]
    public static extern int SystemParametersInfo(int uAction, int uParam, string lpvParam, int fuWinIni);
}}
"@
[Wallpaper]::SystemParametersInfo(20, 0, '{path}', 3)
"""
    console.print(f"[bold cyan]🖼  Setting wallpaper:[/bold cyan] {path}")
    run_powershell(ps)
