"""Modern responsive dark-mode Dashboard HTML/CSS/JS template."""

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Rudra Command Center</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    body { background-color: #0b0f19; color: #e2e8f0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    .glass { background: rgba(17, 24, 39, 0.7); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.08); }
    .glass-card { background: rgba(30, 41, 59, 0.5); backdrop-filter: blur(8px); border: 1px solid rgba(255,255,255,0.05); }
    .gauge-bar { transition: width 0.6s cubic-bezier(0.4,0,0.2,1); }
    .log-box { background: #030712; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
    .copy-btn { opacity: 0; transition: opacity 0.15s; }
    .cmd-row:hover .copy-btn { opacity: 1; }
  </style>
</head>
<body class="min-h-screen flex flex-col">

  <!-- Navbar -->
  <header class="glass sticky top-0 z-50 px-6 py-4 flex items-center justify-between border-b border-slate-800">
    <div class="flex items-center space-x-3">
      <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
        <i class="fa-solid fa-bolt text-white text-lg"></i>
      </div>
      <div>
        <h1 class="text-xl font-bold tracking-tight bg-gradient-to-r from-white via-slate-200 to-cyan-400 bg-clip-text text-transparent">RUDRA</h1>
        <p class="text-xs text-slate-400">System Command & Intelligence Suite</p>
      </div>
    </div>
    <div class="flex items-center space-x-4">
      <button onclick="runOptimize()" class="px-4 py-2 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white rounded-lg text-sm font-medium transition shadow-lg shadow-cyan-500/20 flex items-center space-x-2">
        <i class="fa-solid fa-wand-magic-sparkles"></i><span>Quick Optimize</span>
      </button>
      <div class="px-3 py-1 bg-slate-800/80 border border-slate-700 rounded-full text-xs text-cyan-400 font-mono flex items-center space-x-2">
        <span class="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
        <span id="hostname-text">Connecting...</span>
      </div>
    </div>
  </header>

  <!-- Main -->
  <main class="flex-1 max-w-7xl w-full mx-auto p-6 space-y-6">

    <!-- Tabs -->
    <div class="flex space-x-2 border-b border-slate-800 pb-2 overflow-x-auto">
      <button onclick="switchTab('overview')" id="tab-overview" class="tab-btn active-tab px-4 py-2 rounded-lg text-sm font-medium flex items-center space-x-2 shrink-0">
        <i class="fa-solid fa-gauge-high"></i><span>Overview</span>
      </button>
      <button onclick="switchTab('commands')" id="tab-commands" class="tab-btn px-4 py-2 rounded-lg text-sm font-medium text-slate-400 hover:text-white transition flex items-center space-x-2 shrink-0">
        <i class="fa-solid fa-book-open"></i><span>Command Reference</span>
      </button>
      <button onclick="switchTab('logs')" id="tab-logs" class="tab-btn px-4 py-2 rounded-lg text-sm font-medium text-slate-400 hover:text-white transition flex items-center space-x-2 shrink-0">
        <i class="fa-solid fa-scroll"></i><span>Logs</span>
      </button>
      <button onclick="switchTab('services')" id="tab-services" class="tab-btn px-4 py-2 rounded-lg text-sm font-medium text-slate-400 hover:text-white transition flex items-center space-x-2 shrink-0">
        <i class="fa-solid fa-gears"></i><span>Services</span>
      </button>
      <button onclick="switchTab('security')" id="tab-security" class="tab-btn px-4 py-2 rounded-lg text-sm font-medium text-slate-400 hover:text-white transition flex items-center space-x-2 shrink-0">
        <i class="fa-solid fa-shield-halved"></i><span>Security</span>
      </button>
      <button onclick="switchTab('labs')" id="tab-labs" class="tab-btn px-4 py-2 rounded-lg text-sm font-medium text-slate-400 hover:text-white transition flex items-center space-x-2 shrink-0">
        <i class="fa-solid fa-flask"></i><span>Rudra Lab</span>
      </button>
      <button onclick="switchTab('osint')" id="tab-osint" class="tab-btn px-4 py-2 rounded-lg text-sm font-medium text-slate-400 hover:text-white transition flex items-center space-x-2 shrink-0">
        <i class="fa-solid fa-user-secret"></i><span>OSINT Dossiers</span>
      </button>
    </div>

    <!-- ── TAB: OVERVIEW ─────────────────────────────────────────── -->
    <div id="content-overview" class="tab-content space-y-6">
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div class="glass-card p-5 rounded-2xl">
          <div class="flex items-center justify-between mb-3">
            <span class="text-xs font-semibold text-slate-400 uppercase tracking-wider">CPU Load</span>
            <i class="fa-solid fa-microchip text-cyan-400 text-lg"></i>
          </div>
          <div class="text-2xl font-bold text-white mb-2" id="cpu-val">0.00</div>
          <div class="text-xs text-slate-400" id="cpu-sub">1m / 5m / 15m</div>
        </div>
        <div class="glass-card p-5 rounded-2xl">
          <div class="flex items-center justify-between mb-3">
            <span class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Memory (RAM)</span>
            <i class="fa-solid fa-memory text-purple-400 text-lg"></i>
          </div>
          <div class="text-2xl font-bold text-white mb-2" id="ram-val">0%</div>
          <div class="w-full bg-slate-800 rounded-full h-2 mb-2 overflow-hidden">
            <div id="ram-bar" class="gauge-bar bg-gradient-to-r from-purple-500 to-indigo-500 h-2 rounded-full" style="width:0%"></div>
          </div>
          <div class="text-xs text-slate-400" id="ram-sub">0 / 0 MB</div>
        </div>
        <div class="glass-card p-5 rounded-2xl">
          <div class="flex items-center justify-between mb-3">
            <span class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Root Disk</span>
            <i class="fa-solid fa-hard-drive text-emerald-400 text-lg"></i>
          </div>
          <div class="text-2xl font-bold text-white mb-2" id="disk-val">0%</div>
          <div class="w-full bg-slate-800 rounded-full h-2 mb-2 overflow-hidden">
            <div id="disk-bar" class="gauge-bar bg-gradient-to-r from-emerald-500 to-teal-500 h-2 rounded-full" style="width:0%"></div>
          </div>
          <div class="text-xs text-slate-400" id="disk-sub">0 / 0 GB</div>
        </div>
        <div class="glass-card p-5 rounded-2xl">
          <div class="flex items-center justify-between mb-3">
            <span class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Uptime</span>
            <i class="fa-solid fa-clock text-amber-400 text-lg"></i>
          </div>
          <div class="text-2xl font-bold text-white mb-2" id="uptime-val">--</div>
          <div class="text-xs text-slate-400" id="kernel-sub">Linux Kernel</div>
        </div>
      </div>

      <div class="glass p-6 rounded-2xl">
        <h2 class="text-lg font-semibold text-white mb-4 flex items-center space-x-2">
          <i class="fa-solid fa-sliders text-cyan-400"></i><span>Quick Actions</span>
        </h2>
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <button onclick="runOptimize()" class="p-4 bg-slate-800/80 hover:bg-slate-800 border border-slate-700/80 rounded-xl flex items-center space-x-3 transition group">
            <div class="w-10 h-10 rounded-lg bg-cyan-500/10 text-cyan-400 flex items-center justify-center group-hover:scale-110 transition"><i class="fa-solid fa-broom"></i></div>
            <div class="text-left"><div class="text-sm font-semibold text-white">System Optimize</div><div class="text-xs text-slate-400">Clean caches, trim logs, SSD TRIM</div></div>
          </button>
          <button onclick="switchTab('commands')" class="p-4 bg-slate-800/80 hover:bg-slate-800 border border-slate-700/80 rounded-xl flex items-center space-x-3 transition group">
            <div class="w-10 h-10 rounded-lg bg-purple-500/10 text-purple-400 flex items-center justify-center group-hover:scale-110 transition"><i class="fa-solid fa-book-open"></i></div>
            <div class="text-left"><div class="text-sm font-semibold text-white">Command Reference</div><div class="text-xs text-slate-400">Browse all Rudra commands</div></div>
          </button>
          <button onclick="switchTab('osint')" class="p-4 bg-slate-800/80 hover:bg-slate-800 border border-slate-700/80 rounded-xl flex items-center space-x-3 transition group">
            <div class="w-10 h-10 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center group-hover:scale-110 transition"><i class="fa-solid fa-fingerprint"></i></div>
            <div class="text-left"><div class="text-sm font-semibold text-white">OSINT Intelligence</div><div class="text-xs text-slate-400">Target footprinting & reports</div></div>
          </button>
        </div>
      </div>
    </div>

    <!-- ── TAB: COMMAND REFERENCE ────────────────────────────────── -->
    <div id="content-commands" class="tab-content hidden space-y-4">
      <div class="glass p-6 rounded-2xl">
        <div class="flex items-center justify-between mb-4 flex-wrap gap-3">
          <h2 class="text-lg font-semibold text-white flex items-center space-x-2">
            <i class="fa-solid fa-book-open text-cyan-400"></i><span>Rudra Command Reference</span>
          </h2>
          <div class="flex items-center space-x-2">
            <input type="text" id="cmd-filter" oninput="filterCommands()" placeholder="Filter commands…"
              class="px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white focus:outline-none focus:border-cyan-500 w-56">
            <select id="cat-filter" onchange="filterCommands()"
              class="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white focus:outline-none focus:border-cyan-500">
              <option value="">All categories</option>
            </select>
          </div>
        </div>
        <div id="commands-container" class="space-y-6">
          <div class="text-slate-500 text-center py-6">Loading command reference…</div>
        </div>
      </div>
    </div>

    <!-- ── TAB: LOGS ─────────────────────────────────────────────── -->
    <div id="content-logs" class="tab-content hidden space-y-4">
      <!-- Sub-tabs -->
      <div class="flex space-x-2 mb-2">
        <button onclick="switchLogTab('web')" id="logtab-web" class="log-tab-btn px-3 py-1.5 rounded-lg text-sm font-medium bg-slate-800 text-cyan-400 border border-cyan-500/30">Web Server Log</button>
        <button onclick="switchLogTab('journal')" id="logtab-journal" class="log-tab-btn px-3 py-1.5 rounded-lg text-sm font-medium text-slate-400 hover:text-white transition">System Journal (Warnings)</button>
        <button onclick="reloadLogs()" class="ml-auto px-3 py-1.5 rounded-lg text-sm bg-slate-800 text-slate-400 hover:text-white transition border border-slate-700"><i class="fa-solid fa-rotate-right"></i> Refresh</button>
      </div>

      <div class="glass p-0 rounded-2xl overflow-hidden">
        <div id="log-web" class="log-box p-5 text-xs text-slate-300 h-[70vh] overflow-y-auto whitespace-pre-wrap leading-relaxed">Loading…</div>
        <div id="log-journal" class="log-box p-5 text-xs text-slate-300 h-[70vh] overflow-y-auto whitespace-pre-wrap leading-relaxed hidden">Loading…</div>
      </div>
    </div>

    <!-- ── TAB: SERVICES ─────────────────────────────────────────── -->
    <div id="content-services" class="tab-content hidden space-y-4">
      <div class="glass p-6 rounded-2xl">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-lg font-semibold text-white flex items-center space-x-2">
            <i class="fa-solid fa-gears text-cyan-400"></i><span>Systemd Services</span>
          </h2>
          <input type="text" id="service-filter" oninput="filterServices()" placeholder="Filter services…"
            class="px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white focus:outline-none focus:border-cyan-500">
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-left text-sm">
            <thead class="text-xs text-slate-400 uppercase bg-slate-800/50 border-b border-slate-700">
              <tr>
                <th class="px-4 py-3">Unit</th>
                <th class="px-4 py-3">Status</th>
                <th class="px-4 py-3">Description</th>
              </tr>
            </thead>
            <tbody id="services-tbody" class="divide-y divide-slate-800/60 font-mono text-xs">
              <tr><td colspan="3" class="px-4 py-6 text-center text-slate-500">Loading…</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ── TAB: SECURITY ─────────────────────────────────────────── -->
    <div id="content-security" class="tab-content hidden space-y-4">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div class="glass p-6 rounded-2xl">
          <h3 class="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">Firewall</h3>
          <div class="text-xl font-bold text-white" id="sec-firewall">Checking…</div>
        </div>
        <div class="glass p-6 rounded-2xl">
          <h3 class="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">Fail2ban</h3>
          <div class="text-xl font-bold text-white mb-1" id="sec-fail2ban">Checking…</div>
          <div class="text-xs text-slate-400" id="sec-f2b-banned">0 IPs banned</div>
        </div>
        <div class="glass p-6 rounded-2xl">
          <h3 class="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">AppArmor</h3>
          <div class="text-xl font-bold text-white" id="sec-apparmor">Checking…</div>
        </div>
      </div>
    </div>

    <!-- ── TAB: LABS ─────────────────────────────────────────────── -->
    <div id="content-labs" class="tab-content hidden space-y-4">
      <div class="glass p-6 rounded-2xl">
        <h2 class="text-lg font-semibold text-white mb-4 flex items-center space-x-2">
          <i class="fa-solid fa-flask text-cyan-400"></i><span>Disposable Lab Environments</span>
        </h2>
        <div id="labs-list" class="space-y-3">
          <div class="text-sm text-slate-500 text-center py-4">Loading…</div>
        </div>
      </div>
    </div>

    <!-- ── TAB: OSINT ─────────────────────────────────────────────── -->
    <div id="content-osint" class="tab-content hidden space-y-4">
      <div class="glass p-6 rounded-2xl">
        <h2 class="text-lg font-semibold text-white mb-4 flex items-center space-x-2">
          <i class="fa-solid fa-user-secret text-cyan-400"></i><span>Investigation Dossiers</span>
        </h2>
        <div id="osint-list" class="space-y-3">
          <div class="text-sm text-slate-500 text-center py-4">Loading…</div>
        </div>
      </div>
    </div>

  </main>

  <!-- Copy toast -->
  <div id="copy-toast" class="fixed bottom-6 right-6 px-4 py-2 bg-cyan-600 text-white text-sm rounded-xl shadow-lg opacity-0 transition-opacity duration-300 pointer-events-none">Copied!</div>

  <script>
    // ── Category colours ─────────────────────────────────────────
    const CAT_COLORS = {
      'Core':           'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
      'Packages':       'bg-blue-500/10 text-blue-400 border-blue-500/20',
      'Optimize':       'bg-amber-500/10 text-amber-400 border-amber-500/20',
      'Security':       'bg-red-500/10 text-red-400 border-red-500/20',
      'Archive':        'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',
      'Recon':          'bg-orange-500/10 text-orange-400 border-orange-500/20',
      'Git (plugin)':   'bg-purple-500/10 text-purple-400 border-purple-500/20',
      'Lab (plugin)':   'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
      'OSINT (plugin)': 'bg-rose-500/10 text-rose-400 border-rose-500/20',
      'Web UI (plugin)':'bg-sky-500/10 text-sky-400 border-sky-500/20',
    };
    const catColor = c => CAT_COLORS[c] || 'bg-slate-700/50 text-slate-300 border-slate-600/30';

    let allCommands = [];
    let allServices = [];
    let logsLoaded = false;

    // ── Tab switching ─────────────────────────────────────────────
    function switchTab(name) {
      document.querySelectorAll('.tab-btn').forEach(b => {
        b.classList.remove('bg-slate-800','text-cyan-400','border','border-cyan-500/30');
        b.classList.add('text-slate-400');
      });
      document.querySelectorAll('.tab-content').forEach(c => c.classList.add('hidden'));
      const btn = document.getElementById('tab-' + name);
      btn.classList.add('bg-slate-800','text-cyan-400','border','border-cyan-500/30');
      btn.classList.remove('text-slate-400');
      document.getElementById('content-' + name).classList.remove('hidden');

      if (name === 'commands' && allCommands.length === 0) loadCommands();
      if (name === 'logs' && !logsLoaded) { logsLoaded = true; loadLogs(); }
      if (name === 'services') loadServices();
      if (name === 'security') loadSecurity();
      if (name === 'labs') loadLabs();
      if (name === 'osint') loadOsint();
    }

    // ── Stats ─────────────────────────────────────────────────────
    async function loadStats() {
      try {
        const d = await fetch('/api/system/status').then(r => r.json());
        document.getElementById('hostname-text').innerText = `${d.hostname} (${d.os})`;
        document.getElementById('cpu-val').innerText = d.cpu_load[0];
        document.getElementById('cpu-sub').innerText = `${d.cpu_load[0]} / ${d.cpu_load[1]} / ${d.cpu_load[2]} (${d.cpu_count} cores)`;
        document.getElementById('ram-val').innerText = d.ram.pct + '%';
        document.getElementById('ram-bar').style.width = d.ram.pct + '%';
        document.getElementById('ram-sub').innerText = `${d.ram.used_mb} MB / ${d.ram.total_mb} MB`;
        document.getElementById('disk-val').innerText = d.disk.pct + '%';
        document.getElementById('disk-bar').style.width = d.disk.pct + '%';
        document.getElementById('disk-sub').innerText = `${d.disk.used_gb} GB / ${d.disk.total_gb} GB`;
        document.getElementById('uptime-val').innerText = d.uptime;
        document.getElementById('kernel-sub').innerText = `Kernel ${d.kernel}`;
      } catch (e) { console.error(e); }
    }

    // ── Command Reference ─────────────────────────────────────────
    async function loadCommands() {
      try {
        allCommands = await fetch('/api/commands').then(r => r.json());
        // Populate category filter
        const cats = [...new Set(allCommands.map(c => c.category))];
        const sel = document.getElementById('cat-filter');
        cats.forEach(cat => {
          const o = document.createElement('option'); o.value = cat; o.textContent = cat;
          sel.appendChild(o);
        });
        renderCommands(allCommands);
      } catch (e) { console.error(e); }
    }

    function renderCommands(cmds) {
      const container = document.getElementById('commands-container');
      if (cmds.length === 0) { container.innerHTML = '<div class="text-slate-500 text-center py-6">No commands match your filter.</div>'; return; }
      // Group by category
      const groups = {};
      cmds.forEach(c => { if (!groups[c.category]) groups[c.category] = []; groups[c.category].push(c); });
      container.innerHTML = Object.entries(groups).map(([cat, items]) => `
        <div>
          <div class="flex items-center space-x-2 mb-3">
            <span class="px-2.5 py-1 rounded-lg text-xs font-semibold border ${catColor(cat)}">${cat}</span>
            <span class="text-xs text-slate-500">${items.length} command${items.length > 1 ? 's' : ''}</span>
          </div>
          <div class="space-y-1">
            ${items.map(item => `
              <div class="cmd-row flex items-center justify-between px-4 py-3 bg-slate-800/40 hover:bg-slate-800/70 border border-slate-700/40 rounded-xl transition group">
                <div class="flex items-center space-x-4 min-w-0">
                  <code class="text-cyan-300 text-sm font-mono shrink-0">${escHtml(item.cmd)}</code>
                  <span class="text-xs text-slate-400 truncate">${escHtml(item.desc)}</span>
                </div>
                <button class="copy-btn ml-4 px-2.5 py-1 bg-slate-700 hover:bg-slate-600 text-slate-300 text-xs rounded-lg shrink-0 transition"
                  onclick="copyCmd(event, '${escAttr(item.cmd)}')">
                  <i class="fa-regular fa-copy mr-1"></i>Copy
                </button>
              </div>
            `).join('')}
          </div>
        </div>
      `).join('');
    }

    function filterCommands() {
      const q = document.getElementById('cmd-filter').value.toLowerCase();
      const cat = document.getElementById('cat-filter').value;
      renderCommands(allCommands.filter(c =>
        (!cat || c.category === cat) &&
        (!q || c.cmd.toLowerCase().includes(q) || c.desc.toLowerCase().includes(q))
      ));
    }

    function copyCmd(e, cmd) {
      e.stopPropagation();
      navigator.clipboard.writeText(cmd).then(() => showToast());
    }

    function showToast() {
      const t = document.getElementById('copy-toast');
      t.style.opacity = '1';
      setTimeout(() => t.style.opacity = '0', 1500);
    }

    function escHtml(s) { return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
    function escAttr(s) { return s.replace(/'/g,"\\'"); }

    // ── Logs ──────────────────────────────────────────────────────
    let currentLogTab = 'web';
    async function loadLogs() {
      document.getElementById('log-web').textContent = 'Loading…';
      document.getElementById('log-journal').textContent = 'Loading…';
      try {
        const d = await fetch('/api/logs').then(r => r.json());
        document.getElementById('log-web').textContent = d.web_server || '(empty)';
        document.getElementById('log-journal').textContent = d.system_journal || '(empty)';
        // Scroll to bottom
        ['log-web','log-journal'].forEach(id => {
          const el = document.getElementById(id);
          el.scrollTop = el.scrollHeight;
        });
      } catch (e) { console.error(e); }
    }
    function reloadLogs() { loadLogs(); }
    function switchLogTab(name) {
      currentLogTab = name;
      document.querySelectorAll('.log-tab-btn').forEach(b => {
        b.classList.remove('bg-slate-800','text-cyan-400','border','border-cyan-500/30');
        b.classList.add('text-slate-400');
      });
      document.getElementById('logtab-' + name).classList.add('bg-slate-800','text-cyan-400','border','border-cyan-500/30');
      document.getElementById('logtab-' + name).classList.remove('text-slate-400');
      document.getElementById('log-web').classList.toggle('hidden', name !== 'web');
      document.getElementById('log-journal').classList.toggle('hidden', name !== 'journal');
    }

    // ── Services ──────────────────────────────────────────────────
    async function loadServices() {
      try {
        allServices = await fetch('/api/services').then(r => r.json());
        renderServices(allServices);
      } catch (e) { console.error(e); }
    }
    function renderServices(svcs) {
      document.getElementById('services-tbody').innerHTML = svcs.map(s => `
        <tr class="hover:bg-slate-800/40">
          <td class="px-4 py-3 font-semibold text-white">${s.unit}</td>
          <td class="px-4 py-3"><span class="px-2 py-0.5 rounded-full text-[10px] ${s.active ? 'bg-green-500/10 text-green-400 border border-green-500/20' : 'bg-slate-700/50 text-slate-400'}">${s.state}</span></td>
          <td class="px-4 py-3 text-slate-400 font-sans text-xs">${s.desc || '-'}</td>
        </tr>
      `).join('');
    }
    function filterServices() {
      const q = document.getElementById('service-filter').value.toLowerCase();
      renderServices(allServices.filter(s => s.unit.toLowerCase().includes(q) || s.desc.toLowerCase().includes(q)));
    }

    // ── Security ──────────────────────────────────────────────────
    async function loadSecurity() {
      try {
        const d = await fetch('/api/security').then(r => r.json());
        document.getElementById('sec-firewall').innerText = d.firewall;
        document.getElementById('sec-fail2ban').innerText = d.fail2ban;
        document.getElementById('sec-f2b-banned').innerText = `${d.fail2ban_banned} IPs currently banned`;
        document.getElementById('sec-apparmor').innerText = d.apparmor;
      } catch (e) { console.error(e); }
    }

    // ── Labs ──────────────────────────────────────────────────────
    async function loadLabs() {
      try {
        const data = await fetch('/api/lab').then(r => r.json());
        const c = document.getElementById('labs-list');
        c.innerHTML = data.length === 0
          ? '<div class="text-slate-500 text-center py-6">No lab environments. Spawn one with <code class="text-cyan-400">rudra lab create &lt;name&gt;</code>.</div>'
          : data.map(l => `
            <div class="p-4 bg-slate-800/50 border border-slate-700/60 rounded-xl flex items-center justify-between">
              <div><div class="font-semibold text-white">${l.name}</div><div class="text-xs text-slate-400">Tier: ${l.tier} | Path: ${l.path}</div></div>
              <span class="px-2.5 py-1 bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 rounded-md text-xs font-mono">Isolated</span>
            </div>
          `).join('');
      } catch (e) { console.error(e); }
    }

    // ── OSINT ─────────────────────────────────────────────────────
    async function loadOsint() {
      try {
        const data = await fetch('/api/osint').then(r => r.json());
        const c = document.getElementById('osint-list');
        c.innerHTML = data.length === 0
          ? '<div class="text-slate-500 text-center py-6">No OSINT dossiers yet. Run <code class="text-cyan-400">rudra osint &lt;target&gt;</code>.</div>'
          : data.map(r => `
            <div class="p-4 bg-slate-800/50 border border-slate-700/60 rounded-xl flex items-center justify-between hover:bg-slate-800 transition">
              <div>
                <div class="font-semibold text-cyan-400 font-mono text-sm">${r.filename}</div>
                <div class="text-xs text-slate-400">Modified: ${r.modified} | Size: ${r.size_kb} KB</div>
              </div>
              <span class="px-3 py-1 bg-slate-700/60 text-slate-300 rounded text-xs">Markdown</span>
            </div>
          `).join('');
      } catch (e) { console.error(e); }
    }

    // ── Optimize ──────────────────────────────────────────────────
    async function runOptimize() {
      if (!confirm('Run full system optimization now? This cleans caches, journals, and runs SSD TRIM.')) return;
      try {
        const r = await fetch('/api/system/optimize', { method: 'POST' });
        const d = await r.json();
        alert(d.status === 'success' ? '✓ Optimization complete!' : 'Error: ' + d.message);
        loadStats();
      } catch (e) { alert('Optimization failed: ' + e); }
    }

    // ── Boot ──────────────────────────────────────────────────────
    loadStats();
    setInterval(loadStats, 5000);
  </script>
</body>
</html>
"""
