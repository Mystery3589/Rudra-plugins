import React, { useEffect, useRef, useState } from "react";
import { Terminal as Xterm } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import { WebLinksAddon } from "@xterm/addon-web-links";
import { Terminal as TermIcon, Play, Trash2 } from "lucide-react";
import "@xterm/xterm/css/xterm.css";

interface TerminalViewProps {
  onExecute: (tokens: string[]) => void;
  isRunning: boolean;
  termInstanceRef: React.MutableRefObject<Xterm | null>;
}

export const TerminalView: React.FC<TerminalViewProps> = ({ onExecute, isRunning, termInstanceRef }) => {
  const mountRef = useRef<HTMLDivElement>(null);
  const fitRef = useRef<FitAddon | null>(null);
  const [customCmd, setCustomCmd] = useState("");

  useEffect(() => {
    if (!mountRef.current) return;

    const term = new Xterm({
      cursorBlink: true,
      fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
      fontSize: 13,
      lineHeight: 1.3,
      theme: {
        background: "#000000",
        foreground: "#e2e8f0",
        cursor: "#6366f1",
        selectionBackground: "rgba(99, 102, 241, 0.35)",
        black: "#0a0d14",
        red: "#f43f5e",
        green: "#10b981",
        yellow: "#f59e0b",
        blue: "#6366f1",
        magenta: "#a855f7",
        cyan: "#06b6d4",
        white: "#f8fafc",
        brightRed: "#fb7185",
        brightGreen: "#34d399",
        brightBlue: "#818cf8",
        brightCyan: "#22d3ee",
      }
    });

    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.loadAddon(new WebLinksAddon());
    term.open(mountRef.current);
    fitAddon.fit();

    termInstanceRef.current = term;
    fitRef.current = fitAddon;

    term.writeln("\x1b[1;38;2;99;102;241m\u{1F531} RUDRA TERMINAL HUD \u2014 FULLSCREEN MODE\x1b[0m");
    term.writeln("\x1b[90mxterm-256color streaming. Type any command or pick a preset below.\x1b[0m\r\n");

    const handleResize = () => fitAddon.fit();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!customCmd.trim()) return;
    const parts = customCmd.trim().split(/\s+/);
    onExecute(parts);
    setCustomCmd("");
  };

  const presets = [
    { label: "\u26a1 System Optimize (Dry-Run)", tokens: ["rudra", "system", "optimize", "--dry-run"] },
    { label: "\ud83e\ude7a Driver Doctor", tokens: ["rudra", "driver", "doctor"] },
    { label: "\ud83d\udd0d Git Security Audit", tokens: ["rudra", "git", "audit"] },
    { label: "\ud83e\uddea Lab Cleanup", tokens: ["rudra", "lab", "cleanup"] },
    { label: "\ud83e\ude9f Win Debloat", tokens: ["rudra", "win", "debloat"] },
    { label: "\ud83d\udca5 Chaos Engineering", tokens: ["rudra", "lab", "chaos", "--all"] },
    { label: "\ud83d\udc19 Git Blame Game", tokens: ["rudra", "git", "blame-game"] },
  ];

  return (
    <div className="flex-1 flex flex-col overflow-hidden p-5 gap-3">
      {/* Header */}
      <div className="flex items-center justify-between shrink-0 border-b border-white/10 pb-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
            <TermIcon className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-base font-bold text-white">Warp-Grade Interactive Terminal</h1>
            <p className="text-xs text-slate-400">xterm-256color · Real-time ANSI color streaming</p>
          </div>
        </div>
        <button
          onClick={() => {
            termInstanceRef.current?.clear();
            termInstanceRef.current?.writeln("\x1b[90mBuffer cleared.\x1b[0m\r\n");
          }}
          className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-xs font-semibold text-slate-300 flex items-center gap-1.5"
        >
          <Trash2 className="w-3.5 h-3.5" />
          <span>Clear</span>
        </button>
      </div>

      {/* Preset chips */}
      <div className="flex gap-2 overflow-x-auto shrink-0 pb-1 scrollbar-none">
        {presets.map((c, i) => (
          <button
            key={i}
            onClick={() => onExecute(c.tokens)}
            className="px-3 py-1.5 rounded-xl bg-white/[0.03] hover:bg-indigo-500/20 hover:border-indigo-500/40 border border-white/10 text-xs font-mono text-slate-300 whitespace-nowrap transition-all"
          >
            {c.label}
          </button>
        ))}
      </div>

      {/* xterm viewport */}
      <div className="flex-1 rounded-2xl border border-white/10 bg-black overflow-hidden flex flex-col shadow-2xl min-h-0">
        <div className="h-9 bg-[#080c14] border-b border-white/10 px-4 flex items-center gap-1.5 shrink-0">
          <div className="w-2.5 h-2.5 rounded-full bg-rose-500" />
          <div className="w-2.5 h-2.5 rounded-full bg-amber-500" />
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
          <span className="text-[11px] font-mono text-slate-400 ml-2">rudra-session</span>
          {isRunning && (
            <span className="ml-auto flex items-center gap-1 text-[10px] font-mono text-emerald-400 animate-pulse">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              RUNNING
            </span>
          )}
        </div>
        <div ref={mountRef} className="flex-1 p-2 overflow-hidden" />
      </div>

      {/* Command input */}
      <form onSubmit={handleSubmit} className="shrink-0 flex gap-2">
        <div className="flex-1 bg-surface border border-white/10 rounded-xl px-4 py-2.5 font-mono text-xs flex items-center gap-2 focus-within:border-indigo-500 transition-all">
          <span className="text-indigo-400 font-extrabold">$</span>
          <input
            type="text"
            value={customCmd}
            onChange={(e) => setCustomCmd(e.target.value)}
            placeholder="rudra system clean --all · rudra ask 'why is my disk full' · rudra git graph"
            className="w-full bg-transparent text-slate-100 placeholder-slate-500 focus:outline-none"
          />
        </div>
        <button
          type="submit"
          disabled={isRunning || !customCmd.trim()}
          className="px-6 py-2.5 rounded-xl bg-indigo-500 hover:bg-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold text-xs flex items-center gap-2 shadow-glow transition-all"
        >
          <Play className="w-3.5 h-3.5 fill-current" />
          <span>Run</span>
        </button>
      </form>
    </div>
  );
};
