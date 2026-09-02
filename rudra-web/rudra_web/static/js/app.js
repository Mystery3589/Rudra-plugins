/**
 * Rudra Professional Developer Workstation
 * Dynamic Schema Canvas, Mouse Hover Spotlight, Raycast Palette & xterm.js HUD
 */

let schemaData = null;
let currentGroup = null;
let currentCmd = null;
let term = null;
let fitAddon = null;
let activeWs = null;
let currentThemeIndex = 0;
const THEMES = ['theme-indigo', 'theme-tokyo', 'theme-cyberpunk', 'theme-matrix'];

const GROUP_ICONS = {
  system: '⚡',
  driver: '🚗',
  drivers: '🚗',
  oracle: '🔮',
  git: '🐙',
  lab: '🧪',
  win: '🪟',
  security: '🛡️',
  heal: '🩺',
  project: '🎯',
  'recon-tools': '📡',
  setup: '🚀',
  archive: '📦',
  plugin: '🧩',
  theme: '🎨',
  web: '🌐',
  pkg: '📦',
  packages: '📦',
  service: '⚙️',
  general: '🔱'
};

document.addEventListener('DOMContentLoaded', async () => {
  initTerminal();
  initMouseSpotlight();
  await loadTelemetry();
  await loadSchema();
  setupEventListeners();
});

/* ── 1. Dynamic Mouse-Follow Hover Lighting Spotlight ── */
function initMouseSpotlight() {
  window.addEventListener('mousemove', (e) => {
    document.documentElement.style.setProperty('--mouse-x', `${e.clientX}px`);
    document.documentElement.style.setProperty('--mouse-y', `${e.clientY}px`);
  });
}

/* ── 2. Terminal Engine Initialization ── */
function initTerminal() {
  term = new Terminal({
    cursorBlink: true,
    fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
    fontSize: 13,
    lineHeight: 1.28,
    letterSpacing: 0,
    theme: {
      background: '#000000',
      foreground: '#e2e8f0',
      cursor: '#6366f1',
      selectionBackground: 'rgba(99, 102, 241, 0.35)',
      black: '#0a0d14',
      red: '#f43f5e',
      green: '#10b981',
      yellow: '#f59e0b',
      blue: '#6366f1',
      magenta: '#a855f7',
      cyan: '#06b6d4',
      white: '#f8fafc',
      brightBlack: '#475569',
      brightRed: '#fb7185',
      brightGreen: '#34d399',
      brightYellow: '#fbbf24',
      brightBlue: '#818cf8',
      brightMagenta: '#c084fc',
      brightCyan: '#22d3ee',
      brightWhite: '#ffffff',
    }
  });

  fitAddon = new FitAddon.FitAddon();
  term.loadAddon(fitAddon);
  term.open(document.getElementById('terminal'));
  fitAddon.fit();
  window.addEventListener('resize', () => fitAddon.fit());

  term.writeln('\x1b[1;38;2;99;102;241m🔱 RUDRA PROFESSIONAL DEVELOPER WORKSTATION\x1b[0m');
  term.writeln('\x1b[90mConnected to live schema engine. Ready for execution.\x1b[0m\r\n');
}

/* ── 3. Telemetry & Sudo Status ── */
async function loadTelemetry() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();
    document.getElementById('os-telemetry').innerText = `${data.os} (${data.machine})`;
    
    const sudoBtn = document.getElementById('sudo-badge-btn');
    if (data.has_nopasswd_sudo) {
      sudoBtn.innerHTML = '<span>⚡</span> Sudo: NOPASSWD';
      sudoBtn.classList.add('sudo-unlocked');
    } else {
      sudoBtn.innerHTML = '<span>🔑</span> Sudo Lock';
    }
  } catch (err) {
    console.error('Failed to load telemetry:', err);
  }
}

/* ── 4. Schema Engine & Categories ── */
async function loadSchema() {
  try {
    const res = await fetch('/api/schema');
    schemaData = await res.json();
    renderCategories();
    
    if (schemaData.group_names && schemaData.group_names.length > 0) {
      const initialGroup = schemaData.group_names.includes('system') ? 'system' : schemaData.group_names[0];
      selectCategory(initialGroup);
    }
  } catch (err) {
    term.writeln(`\x1b[1;31m✖ Error loading schema: ${err.message}\x1b[0m`);
  }
}

function renderCategories() {
  const container = document.getElementById('categories-tabs');
  container.innerHTML = '';

  schemaData.group_names.forEach(grp => {
    const icon = GROUP_ICONS[grp] || '📁';
    const btn = document.createElement('button');
    btn.className = `category-tab-btn ${grp === currentGroup ? 'active' : ''}`;
    btn.innerHTML = `<span>${icon}</span> ${grp.toUpperCase()}`;
    btn.onclick = () => selectCategory(grp);
    container.appendChild(btn);
  });
}

function selectCategory(groupName) {
  currentGroup = groupName;
  renderCategories();
  renderSidebarCommands();
  const cmds = schemaData.groups[groupName] || [];
  if (cmds.length > 0) {
    selectCommand(cmds[0]);
  }
}

function renderSidebarCommands(query = '') {
  const container = document.getElementById('commands-list');
  container.innerHTML = '';
  const cmds = schemaData.groups[currentGroup] || [];
  
  const filtered = cmds.filter(c => 
    c.name.toLowerCase().includes(query.toLowerCase()) || 
    c.help.toLowerCase().includes(query.toLowerCase()) ||
    c.command_str.toLowerCase().includes(query.toLowerCase())
  );

  filtered.forEach(cmd => {
    const item = document.createElement('div');
    const isSelected = currentCmd && currentCmd.command_str === cmd.command_str;
    item.className = `cmd-card-item ${isSelected ? 'active' : ''}`;
    
    item.innerHTML = `
      <div class="cmd-card-header">
        <span class="cmd-card-title">${cmd.name}</span>
        ${cmd.params.some(p => p.flags.includes('--dry-run')) ? '<span class="hero-badge" style="font-size:0.6rem; color:var(--accent-amber);">dry-run</span>' : ''}
      </div>
      <div class="cmd-card-help">${cmd.help || 'No description provided.'}</div>
    `;

    item.onclick = () => selectCommand(cmd);
    container.appendChild(item);
  });
}

function selectCommand(cmd) {
  currentCmd = cmd;
  renderSidebarCommands(document.getElementById('sidebar-search-input').value);
  renderParameterCanvas(cmd);
  updateLiveSyntaxBar();
}

/* ── 5. Dynamic Parameter Canvas (Form Deck) ── */
function renderParameterCanvas(cmd) {
  const icon = GROUP_ICONS[currentGroup] || '🔱';
  
  document.getElementById('crumb-group').innerText = currentGroup.toUpperCase();
  document.getElementById('crumb-cmd').innerText = cmd.name;

  document.getElementById('hero-title').innerHTML = `<span>${icon}</span> <span class="hero-title-command">${cmd.command_str}</span>`;
  document.getElementById('hero-desc').innerText = cmd.help || 'Execute command across your infrastructure.';
  
  const badgesRow = document.getElementById('hero-badges-row');
  badgesRow.innerHTML = `
    <span class="hero-badge">Group: ${currentGroup}</span>
    <span class="hero-badge">Path: ${cmd.full_path.join(' ')}</span>
    <span class="hero-badge">${cmd.params.length} Flag${cmd.params.length === 1 ? '' : 's'} / Param${cmd.params.length === 1 ? '' : 's'}</span>
  `;

  const grid = document.getElementById('params-grid');
  grid.innerHTML = '';

  if (!cmd.params || cmd.params.length === 0) {
    grid.innerHTML = `
      <div style="grid-column: 1 / -1; padding: 2rem; text-align: center; color: var(--text-muted); font-size: 0.85rem; background: var(--bg-card); border-radius: 10px; border: 1px dashed var(--border-card);">
        ✓ No parameters or options required for this command. Click Execute to launch.
      </div>
    `;
    return;
  }

  cmd.params.forEach(param => {
    const card = document.createElement('div');
    card.className = 'param-card';

    const primaryFlag = param.flags && param.flags.length > 0 ? param.flags[0] : param.name;
    const isRequired = param.required;

    let inputControl = '';

    if (param.type === 'bool' || param.is_flag) {
      inputControl = `
        <label class="spring-switch">
          <input type="checkbox" id="param-${param.name}" data-param="${param.name}" ${param.default ? 'checked' : ''} onchange="updateLiveSyntaxBar()">
          <span class="spring-slider"></span>
        </label>
      `;
    } else if (param.type === 'choice' && param.choices) {
      // High-Craft Segmented Choice Pills
      const pills = param.choices.map(c => `
        <button type="button" class="choice-pill ${c === param.default ? 'active' : ''}" onclick="setChoiceValue('${param.name}', '${c}', this)">
          ${c}
        </button>
      `).join('');
      inputControl = `
        <div class="segmented-choices" id="choice-group-${param.name}" data-value="${param.default || ''}">
          ${pills}
        </div>
      `;
    } else if (param.type === 'int' || param.type === 'float') {
      inputControl = `
        <input type="number" class="custom-input" id="param-${param.name}" data-param="${param.name}" value="${param.default !== null ? param.default : ''}" placeholder="${isRequired ? 'Required number' : 'Optional'}" oninput="updateLiveSyntaxBar()">
      `;
    } else {
      inputControl = `
        <input type="text" class="custom-input" id="param-${param.name}" data-param="${param.name}" value="${param.default || ''}" placeholder="${isRequired ? 'Required value' : 'Optional value...'}" oninput="updateLiveSyntaxBar()">
      `;
    }

    card.innerHTML = `
      <div class="param-header-row">
        <div class="param-flag-title">${primaryFlag} ${isRequired ? '<span style="color:var(--accent-rose)">*</span>' : ''}</div>
        ${param.type === 'bool' || param.is_flag ? inputControl : ''}
      </div>
      ${param.type !== 'bool' && !param.is_flag ? inputControl : ''}
      <div class="param-flag-help">${param.help || (param.is_argument ? 'Positional command argument' : 'Flag / Parameter')}</div>
    `;

    grid.appendChild(card);
  });
}

function setChoiceValue(paramName, val, btnEl) {
  const group = document.getElementById(`choice-group-${paramName}`);
  group.setAttribute('data-value', val);
  group.querySelectorAll('.choice-pill').forEach(p => p.classList.remove('active'));
  btnEl.classList.add('active');
  updateLiveSyntaxBar();
}

/* ── 6. Live Syntax-Highlighted CLI Preview ── */
function buildCommandTokens() {
  if (!currentCmd) return [];
  const args = [...currentCmd.full_path];

  if (currentCmd.params) {
    currentCmd.params.forEach(param => {
      const flag = param.flags && param.flags.length > 0 ? param.flags[0] : null;

      if (param.type === 'bool' || param.is_flag) {
        const el = document.getElementById(`param-${param.name}`);
        if (el && el.checked && flag) {
          args.push(flag);
        }
      } else if (param.type === 'choice' && param.choices) {
        const group = document.getElementById(`choice-group-${param.name}`);
        const val = group ? group.getAttribute('data-value') : '';
        if (val && flag) {
          args.push(flag);
          args.push(val);
        }
      } else {
        const el = document.getElementById(`param-${param.name}`);
        const val = el ? el.value.trim() : '';
        if (val) {
          if (param.is_argument) {
            args.push(val);
          } else if (flag) {
            args.push(flag);
            args.push(val);
          }
        }
      }
    });
  }

  return args;
}

function updateLiveSyntaxBar() {
  const args = buildCommandTokens();
  const box = document.getElementById('cli-code-preview');
  if (args.length === 0) {
    box.innerText = '$ rudra';
    return;
  }

  let html = `<span style="color:var(--brand-primary); font-weight:700;">$ rudra</span> `;
  for (let i = 1; i < args.length; i++) {
    const token = args[i];
    if (token.startsWith('--') || token.startsWith('-')) {
      html += `<span style="color:var(--accent-amber)">${token}</span> `;
    } else if (i === 1) {
      html += `<span style="color:var(--accent-cyan); font-weight:600;">${token}</span> `;
    } else if (i === 2 && !token.startsWith('-')) {
      html += `<span style="color:var(--accent-emerald); font-weight:600;">${token}</span> `;
    } else {
      html += `<span style="color:var(--text-primary)">${token}</span> `;
    }
  }

  box.innerHTML = html;
}

/* ── 7. Streaming Subprocess Execution ── */
function executeCommand(presetArgs = null) {
  const args = presetArgs || buildCommandTokens();
  if (!args || args.length === 0) return;

  const btnRun = document.getElementById('btn-execute');
  const btnAbort = document.getElementById('btn-abort');

  btnRun.disabled = true;
  btnRun.style.display = 'none';
  btnAbort.style.display = 'inline-flex';

  term.writeln(`\r\n\x1b[1;38;2;99;102;241m▶ Executing:\x1b[0m \x1b[1;32m${args.join(' ')}\x1b[0m\r\n`);

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws/run`;

  activeWs = new WebSocket(wsUrl);

  activeWs.onopen = () => {
    activeWs.send(JSON.stringify({ args }));
  };

  activeWs.onmessage = (evt) => {
    try {
      const msg = JSON.parse(evt.data);
      if (msg.type === 'stdout') {
        term.write(msg.data.replace(/\n/g, '\r\n'));
      } else if (msg.type === 'exit') {
        const color = msg.exit_code === 0 ? '\x1b[1;32m' : '\x1b[1;31m';
        term.writeln(`\r\n${color}● Process finished with exit code ${msg.exit_code} (${msg.duration}s)\x1b[0m\r\n`);
        showToast(`Command finished with exit ${msg.exit_code}`);
      } else if (msg.type === 'error') {
        term.writeln(`\r\n\x1b[1;31m✖ Error: ${msg.data}\x1b[0m\r\n`);
      }
    } catch (e) {
      term.write(evt.data);
    }
  };

  activeWs.onclose = () => {
    btnRun.disabled = false;
    btnRun.style.display = 'inline-flex';
    btnAbort.style.display = 'none';
    fitAddon.fit();
  };

  activeWs.onerror = () => {
    term.writeln(`\r\n\x1b[1;31m✖ Execution WebSocket disconnected.\x1b[0m\r\n`);
    btnRun.disabled = false;
    btnRun.style.display = 'inline-flex';
    btnAbort.style.display = 'none';
  };
}

function abortExecution() {
  if (activeWs) {
    activeWs.close();
    term.writeln(`\r\n\x1b[1;33m⏹ Process execution terminated by user.\x1b[0m\r\n`);
  }
}

/* ── 8. Global Events & Command Palette (Ctrl+K) ── */
function setupEventListeners() {
  document.getElementById('sidebar-search-input').addEventListener('input', (e) => {
    renderSidebarCommands(e.target.value);
  });

  document.getElementById('btn-execute').addEventListener('click', () => executeCommand());
  document.getElementById('btn-abort').addEventListener('click', abortExecution);

  // Command Palette Trigger: Ctrl+K / Cmd+K
  window.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      openCommandPalette();
    }
  });
}

function openCommandPalette() {
  document.getElementById('palette-modal').style.display = 'flex';
  const input = document.getElementById('palette-input');
  input.value = '';
  input.focus();
  renderPaletteResults('');
}

function closeCommandPalette() {
  document.getElementById('palette-modal').style.display = 'none';
}

function renderPaletteResults(query = '') {
  const container = document.getElementById('palette-results');
  container.innerHTML = '';
  if (!schemaData) return;

  const allCmds = [];
  schemaData.group_names.forEach(g => {
    const list = schemaData.groups[g] || [];
    list.forEach(c => allCmds.push({ group: g, ...c }));
  });

  const matches = allCmds.filter(c => 
    c.name.toLowerCase().includes(query.toLowerCase()) || 
    c.help.toLowerCase().includes(query.toLowerCase()) ||
    c.command_str.toLowerCase().includes(query.toLowerCase())
  ).slice(0, 8);

  matches.forEach(m => {
    const icon = GROUP_ICONS[m.group] || '🔱';
    const item = document.createElement('div');
    item.className = 'cmd-card-item';
    item.style.padding = '0.75rem 1rem';
    item.innerHTML = `
      <div class="cmd-card-header">
        <span style="color:var(--text-primary); font-weight:700; font-family:var(--font-mono);">${icon} ${m.command_str}</span>
        <span class="hero-badge" style="font-size:0.65rem;">${m.group}</span>
      </div>
      <div class="cmd-card-help">${m.help}</div>
    `;
    item.onclick = () => {
      closeCommandPalette();
      selectCategory(m.group);
      selectCommand(m);
    };
    container.appendChild(item);
  });
}

/* ── 9. Utilities & Modals ── */
function copyCommandText() {
  const args = buildCommandTokens();
  const text = args.join(' ');
  navigator.clipboard.writeText(text);
  showToast('✓ Command copied to clipboard');
}

function showToast(msg) {
  const toast = document.getElementById('toast-notice');
  toast.innerHTML = `<span>⚡</span> <span>${msg}</span>`;
  toast.style.display = 'flex';
  setTimeout(() => { toast.style.display = 'none'; }, 2200);
}

function clearTerminal() {
  term.clear();
  term.writeln('\x1b[90mTerminal buffer reset.\x1b[0m\r\n');
}

function cycleTheme() {
  currentThemeIndex = (currentThemeIndex + 1) % THEMES.length;
  document.body.className = THEMES[currentThemeIndex];
  showToast(`Switched theme: ${THEMES[currentThemeIndex].replace('theme-', '').toUpperCase()}`);
}

function showSudoModal() {
  document.getElementById('sudo-modal').style.display = 'flex';
  document.getElementById('sudo-input-field').focus();
}

function hideSudoModal() {
  document.getElementById('sudo-modal').style.display = 'none';
}

async function submitSudoPassword() {
  const pw = document.getElementById('sudo-input-field').value;
  if (!pw) return;

  try {
    const res = await fetch('/api/sudo-auth', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: pw })
    });

    if (res.ok) {
      hideSudoModal();
      const sudoBtn = document.getElementById('sudo-badge-btn');
      sudoBtn.innerHTML = '<span>⚡</span> Sudo: Active (RAM)';
      sudoBtn.classList.add('sudo-unlocked');
      showToast('Sudo privileges unlocked for active session');
      term.writeln('\r\n\x1b[1;32m✓ Sudo authentication successful (RAM session cached).\x1b[0m\r\n');
    } else {
      alert('Authentication failed: Invalid sudo password.');
    }
  } catch (err) {
    alert('Error: ' + err.message);
  }
}
