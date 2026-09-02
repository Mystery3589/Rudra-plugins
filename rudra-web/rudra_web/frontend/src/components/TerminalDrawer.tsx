import React, { useEffect, useRef, useState } from 'react';
import { Terminal as Xterm } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import { WebLinksAddon } from '@xterm/addon-web-links';
import { ChevronUp, ChevronDown, Trash2, Copy, Maximize2, Minimize2, Square } from 'lucide-react';
import '@xterm/xterm/css/xterm.css';

interface TerminalDrawerProps {
  isOpen: boolean;
  onToggle: () => void;
  isRunning: boolean;
  onAbort: () => void;
  termInstanceRef: React.MutableRefObject<Xterm | null>;
}

export const TerminalDrawer: React.FC<TerminalDrawerProps> = ({
  isOpen,
  onToggle,
  isRunning,
  onAbort,
  termInstanceRef,
}) => {
  const terminalRef = useRef<HTMLDivElement>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const [isMaximized, setIsMaximized] = useState(false);

  useEffect(() => {
    if (!terminalRef.current || termInstanceRef.current) return;

    const term = new Xterm({
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
      }
    });

    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.loadAddon(new WebLinksAddon());

    term.open(terminalRef.current);
    fitAddon.fit();

    termInstanceRef.current = term;
    fitAddonRef.current = fitAddon;

    const handleResize = () => fitAddon.fit();
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => fitAddonRef.current?.fit(), 150);
    }
  }, [isOpen, isMaximized]);

  if (!isOpen) return null;

  return (
    <div
      className={`fixed bottom-0 right-0 left-16 bg-black/95 backdrop-blur-2xl border-t border-white/15 z-30 transition-all flex flex-col shadow-2xl ${
        isMaximized ? 'top-0 left-16' : 'h-80'
      }`}
    >
      {/* Drawer Header */}
      <div className="h-10 bg-[#080c14] border-b border-white/10 px-4 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full bg-rose-500" />
            <div className="w-2.5 h-2.5 rounded-full bg-amber-500" />
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
          </div>
          <span className="text-xs font-mono font-bold text-slate-300">LIVE EXECUTION TERMINAL</span>
          {isRunning && (
            <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-[10px] font-mono text-emerald-400 animate-pulse">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              RUNNING
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {isRunning && (
            <button
              onClick={onAbort}
              className="px-2.5 py-1 rounded bg-rose-500/20 hover:bg-rose-500/30 border border-rose-500/40 text-rose-300 text-xs font-bold flex items-center gap-1"
            >
              <Square className="w-3 h-3 fill-current" />
              <span>STOP</span>
            </button>
          )}

          <button
            onClick={() => termInstanceRef.current?.clear()}
            className="p-1.5 rounded hover:bg-white/10 text-slate-400 hover:text-slate-200"
            title="Clear"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={() => setIsMaximized(prev => !prev)}
            className="p-1.5 rounded hover:bg-white/10 text-slate-400 hover:text-slate-200"
            title={isMaximized ? 'Restore' : 'Maximize'}
          >
            {isMaximized ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
          </button>

          <button
            onClick={onToggle}
            className="p-1.5 rounded hover:bg-white/10 text-slate-400 hover:text-slate-200"
            title="Collapse"
          >
            <ChevronDown className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Terminal Viewport */}
      <div className="flex-1 p-3 overflow-hidden bg-black">
        <div ref={terminalRef} className="w-full h-full" />
      </div>
    </div>
  );
};
