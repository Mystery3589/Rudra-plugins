"""HTML template for Rudra Interactive Web Terminal powered by xterm.js."""

TERMINAL_PAGE_HTML = """<!DOCTYPE html>
<html lang="en" class="h-full">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Rudra Web Terminal</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/xterm@5.3.0/css/xterm.min.css">
  <script src="https://cdn.jsdelivr.net/npm/xterm@5.3.0/lib/xterm.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/xterm-addon-fit@0.8.0/lib/xterm-addon-fit.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/xterm-addon-web-links@0.9.0/lib/xterm-addon-web-links.min.js"></script>
  <style>
    body { background-color: #080c14; color: #e2e8f0; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
    .glass-bar { background: rgba(15, 23, 42, 0.85); backdrop-filter: blur(12px); border-bottom: 1px solid rgba(255,255,255,0.08); }
    #terminal-container { height: calc(100vh - 56px); }
    .xterm .xterm-viewport { overflow-y: auto; }
  </style>
</head>
<body class="h-full flex flex-col overflow-hidden">

  <!-- Header / Controls Bar -->
  <header class="glass-bar px-5 py-3 flex items-center justify-between shrink-0 select-none z-10">
    <div class="flex items-center space-x-3">
      <div class="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
        <i class="fa-solid fa-terminal text-white text-sm"></i>
      </div>
      <div>
        <h1 class="text-sm font-bold tracking-wide text-white flex items-center space-x-2">
          <span>RUDRA TERMINAL</span>
          <span class="text-[10px] px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-400 font-mono">PTY Interactive</span>
        </h1>
      </div>
    </div>

    <!-- Status & Buttons -->
    <div class="flex items-center space-x-3 text-xs">
      <div id="status-badge" class="px-3 py-1 bg-slate-800/80 border border-slate-700 rounded-full font-mono flex items-center space-x-2 text-slate-300">
        <span id="status-dot" class="w-2 h-2 rounded-full bg-yellow-500"></span>
        <span id="status-text">Connecting...</span>
      </div>

      <div class="h-4 w-px bg-slate-800"></div>

      <!-- Font Controls -->
      <button onclick="changeFontSize(-1)" title="Decrease font" class="p-1.5 px-2 bg-slate-800 hover:bg-slate-700 rounded border border-slate-700 text-slate-300 hover:text-white transition">
        <i class="fa-solid fa-minus"></i>
      </button>
      <button onclick="changeFontSize(1)" title="Increase font" class="p-1.5 px-2 bg-slate-800 hover:bg-slate-700 rounded border border-slate-700 text-slate-300 hover:text-white transition">
        <i class="fa-solid fa-plus"></i>
      </button>

      <!-- Clear Button -->
      <button onclick="clearTerminal()" title="Clear terminal" class="p-1.5 px-2.5 bg-slate-800 hover:bg-slate-700 rounded border border-slate-700 text-slate-300 hover:text-white transition flex items-center space-x-1.5">
        <i class="fa-solid fa-broom"></i><span>Clear</span>
      </button>

      <!-- Reconnect Button -->
      <button onclick="connect()" title="Reconnect session" class="p-1.5 px-2.5 bg-slate-800 hover:bg-slate-700 rounded border border-slate-700 text-cyan-400 hover:text-cyan-300 transition flex items-center space-x-1.5">
        <i class="fa-solid fa-arrows-rotate"></i><span>Reconnect</span>
      </button>

      <!-- Back to Dashboard -->
      <a href="/" title="Open Dashboard" class="p-1.5 px-2.5 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 rounded text-white font-medium transition flex items-center space-x-1.5">
        <i class="fa-solid fa-house"></i><span>Dashboard</span>
      </a>
    </div>
  </header>

  <!-- Terminal Container -->
  <main id="terminal-container" class="w-full flex-1 p-2 bg-[#080c14]"></main>

  <script>
    let term;
    let fitAddon;
    let socket;
    let currentFontSize = 14;

    const rudraTheme = {
      background: '#080c14',
      foreground: '#e2e8f0',
      cursor: '#38bdf8',
      cursorAccent: '#080c14',
      selectionBackground: 'rgba(56, 189, 248, 0.3)',
      black: '#0f172a',
      red: '#f87171',
      green: '#4ade80',
      yellow: '#facc15',
      blue: '#60a5fa',
      magenta: '#c084fc',
      cyan: '#38bdf8',
      white: '#f1f5f9',
      brightBlack: '#475569',
      brightRed: '#ef4444',
      brightGreen: '#22c55e',
      brightYellow: '#eab308',
      brightBlue: '#3b82f6',
      brightMagenta: '#a855f7',
      brightCyan: '#06b6d4',
      brightWhite: '#ffffff'
    };

    function initTerminal() {
      term = new Terminal({
        cursorBlink: true,
        fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
        fontSize: currentFontSize,
        lineHeight: 1.2,
        theme: rudraTheme,
        allowTransparency: true
      });

      fitAddon = new FitAddon.FitAddon();
      term.loadAddon(fitAddon);

      if (window.WebLinksAddon) {
        term.loadAddon(new WebLinksAddon.WebLinksAddon());
      }

      term.open(document.getElementById('terminal-container'));
      fitAddon.fit();

      term.onData(data => {
        if (socket && socket.readyState === WebSocket.OPEN) {
          socket.send(data);
        }
      });

      window.addEventListener('resize', () => {
        if (fitAddon) {
          fitAddon.fit();
          sendResize();
        }
      });
    }

    function sendResize() {
      if (socket && socket.readyState === WebSocket.OPEN && term) {
        socket.send(JSON.stringify({
          type: 'resize',
          cols: term.cols,
          rows: term.rows
        }));
      }
    }

    function setStatus(state, msg) {
      const dot = document.getElementById('status-dot');
      const text = document.getElementById('status-text');
      text.innerText = msg;
      if (state === 'connected') {
        dot.className = 'w-2 h-2 rounded-full bg-green-500 animate-pulse';
        text.className = 'text-green-400 font-mono';
      } else if (state === 'connecting') {
        dot.className = 'w-2 h-2 rounded-full bg-yellow-500 animate-pulse';
        text.className = 'text-yellow-400 font-mono';
      } else {
        dot.className = 'w-2 h-2 rounded-full bg-red-500';
        text.className = 'text-red-400 font-mono';
      }
    }

    function connect() {
      if (socket) {
        socket.close();
      }

      setStatus('connecting', 'Connecting...');
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws/terminal`;

      socket = new WebSocket(wsUrl);

      socket.onopen = () => {
        setStatus('connected', 'Connected');
        sendResize();
        term.focus();
      };

      socket.onmessage = event => {
        term.write(event.data);
      };

      socket.onclose = () => {
        setStatus('disconnected', 'Session Closed');
        term.write('\\r\\n\\x1b[31m[Session closed. Click Reconnect to restart]\\x1b[0m\\r\\n');
      };

      socket.onerror = () => {
        setStatus('disconnected', 'Connection Error');
      };
    }

    function clearTerminal() {
      if (term) term.clear();
    }

    function changeFontSize(delta) {
      currentFontSize = Math.max(10, Math.min(26, currentFontSize + delta));
      if (term && fitAddon) {
        term.options.fontSize = currentFontSize;
        fitAddon.fit();
        sendResize();
      }
    }

    // Launch
    window.addEventListener('DOMContentLoaded', () => {
      initTerminal();
      connect();
    });
  </script>
</body>
</html>
"""
