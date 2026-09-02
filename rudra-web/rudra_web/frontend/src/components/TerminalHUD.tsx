import React, { useEffect, useRef } from 'react';
import { Trash2, Copy, Maximize2, Minimize2, Terminal as TermIcon } from 'lucide-react';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import { WebLinksAddon } from '@xterm/addon-web-links';
import '@xterm/xterm/css/xterm.css';

interface TerminalHUDProps {
  onClear: () => void;
  onCopyOutput: () => void;
  onPresetClick: (args: string[]) => void;
  termInstanceRef: React.MutableRefObject<Terminal | null>;
}

export const TerminalHUD: React.FC<TerminalHUDProps> = ({
  onClear,
  onCopyOutput,
  onPresetClick,
  termInstanceRef
}) => {
  const terminalRef = useRef<HTMLDivElement>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);

  useEffect(() => {
    if (!terminalRef.current) return;

    const term = new Terminal({
      cursorBlink: true,
      fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
      fontSize: 12.5,
      lineHeight: 1.25,
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

    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.loadAddon(new WebLinksAddon());

    term.open(terminalRef.current);
    fitAddon.fit();

    termInstanceRef.current = term;
    fitAddonRef.current = fitAddon;

    term.writeln('\x1b[1;38;2;99;102;241m🔱 RUDRA DEVELOPER WORKSTATION HUD\x1b[0m');
    term.writeln('\x1b[90mTTY: xterm-256color streaming active.\x1b[0m\r\n');

    const handleResize = () => fitAddon.fit();
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      term.dispose();
    };
  }, []);

  return (
    <section className="w-[480px] bg-black border-l border-white/10 flex flex-col overflow-hidden shrink-0">
      {/* Terminal Titlebar */}
      <div className="h-10 bg-[#080c14] border-b border-white/10 px-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-1.5">
          <div className="w-2.5 h-2.5 rounded-full bg-rose-500" />
          <div className="w-2.5 h-2.5 rounded-full bg-amber-500" />
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
          <span className="text-[11px] font-mono text-slate-400 ml-2">OUTPUT TERMINAL</span>
        </div>

        <div className="flex items-center gap-1">
          <button
            onClick={onClear}
            className="p-1 rounded hover:bg-white/10 text-slate-400 hover:text-slate-200 text-xs"
            title="Clear buffer"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={onCopyOutput}
            className="p-1 rounded hover:bg-white/10 text-slate-400 hover:text-slate-200 text-xs"
            title="Copy logs"
          >
            <Copy className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* xterm.js stage */}
      <div className="flex-1 p-2 overflow-hidden bg-black">
        <div ref={terminalRef} className="w-full h-full" />
      </div>

      {/* Workflow Preset Chips */}
      <div className="p-2 bg-[#06090e] border-t border-white/10 flex gap-1.5 overflow-x-auto scrollbar-none shrink-0">
        <button
          onClick={() => onPresetClick(['rudra', 'system', 'optimize', '--dry-run'])}
          className="px-2.5 py-1 rounded bg-white/[0.04] hover:bg-indigo-500/20 hover:text-indigo-400 border border-white/10 text-[11px] font-mono whitespace-nowrap text-slate-300 transition-all"
        >
          ⚡ Optimize (Dry-Run)
        </button>
        <button
          onClick={() => onPresetClick(['rudra', 'driver', 'doctor'])}
          className="px-2.5 py-1 rounded bg-white/[0.04] hover:bg-indigo-500/20 hover:text-indigo-400 border border-white/10 text-[11px] font-mono whitespace-nowrap text-slate-300 transition-all"
        >
          🚗 Driver Doctor
        </button>
        <button
          onClick={() => onPresetClick(['rudra', 'git', 'audit'])}
          className="px-2.5 py-1 rounded bg-white/[0.04] hover:bg-indigo-500/20 hover:text-indigo-400 border border-white/10 text-[11px] font-mono whitespace-nowrap text-slate-300 transition-all"
        >
          🔍 Git Audit
        </button>
        <button
          onClick={() => onPresetClick(['rudra', 'lab', 'cleanup'])}
          className="px-2.5 py-1 rounded bg-white/[0.04] hover:bg-indigo-500/20 hover:text-indigo-400 border border-white/10 text-[11px] font-mono whitespace-nowrap text-slate-300 transition-all"
        >
          🧪 Lab Cleanup
        </button>
      </div>
    </section>
  );
};
