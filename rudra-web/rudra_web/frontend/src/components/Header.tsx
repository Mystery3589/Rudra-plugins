import React from 'react';
import { Command, Shield, Sparkles, History } from 'lucide-react';
import { SystemStatus, ThemeMode } from '../types/schema';

interface HeaderProps {
  status: SystemStatus | null;
  currentGroup: string;
  currentCmd: string;
  theme: ThemeMode;
  onCycleTheme: () => void;
  onOpenPalette: () => void;
  onOpenSudo: () => void;
  onToggleHistory: () => void;
  showHistory: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  status,
  currentGroup,
  currentCmd,
  theme,
  onCycleTheme,
  onOpenPalette,
  onOpenSudo,
  onToggleHistory,
  showHistory
}) => {
  return (
    <header className="h-14 border-b border-white/10 bg-surface/80 backdrop-blur-xl px-4 flex items-center justify-between relative z-40">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 font-extrabold text-base tracking-tight">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-cyan-500 flex items-center justify-center text-lg shadow-glow">
            🔱
          </div>
          <span className="bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
            RUDRA
          </span>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-white/5 border border-white/10 text-slate-400">
            v0.1.0
          </span>
        </div>

        <div className="hidden md:flex items-center gap-2 text-xs font-semibold text-slate-400">
          <span>/</span>
          <span className="text-slate-500 uppercase">{currentGroup || 'SYSTEM'}</span>
          <span>/</span>
          <span className="text-indigo-400 font-mono">{currentCmd || 'optimize'}</span>
        </div>
      </div>

      <div className="flex items-center gap-2.5">
        {status && (
          <div className="hidden sm:flex items-center gap-2 px-3 py-1 rounded-lg bg-white/[0.03] border border-white/10 text-xs font-mono text-slate-300">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_8px_#10b981]" />
            <span>{status.os} ({status.machine})</span>
          </div>
        )}

        <button
          onClick={onOpenPalette}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] border border-white/10 text-xs font-medium text-slate-200 transition-all hover:border-indigo-500/50 hover:shadow-glow"
        >
          <Command className="w-3.5 h-3.5 text-indigo-400" />
          <span>Palette</span>
          <kbd className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white/10 text-slate-400">⌘K</kbd>
        </button>

        <button
          onClick={onOpenSudo}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition-all ${
            status?.has_nopasswd_sudo
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
              : 'bg-amber-500/10 border-amber-500/30 text-amber-400 hover:border-amber-500'
          }`}
        >
          <Shield className="w-3.5 h-3.5" />
          <span>{status?.has_nopasswd_sudo ? 'Sudo: Open' : 'Sudo Auth'}</span>
        </button>

        <button
          onClick={onCycleTheme}
          className="p-2 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] border border-white/10 text-slate-300 transition-all hover:text-indigo-400"
          title="Cycle Theme"
        >
          <Sparkles className="w-4 h-4" />
        </button>

        <button
          onClick={onToggleHistory}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition-all ${
            showHistory
              ? 'bg-indigo-500/20 border-indigo-500 text-indigo-300'
              : 'bg-white/[0.04] hover:bg-white/[0.08] border-white/10 text-slate-300'
          }`}
        >
          <History className="w-3.5 h-3.5" />
          <span>History</span>
        </button>
      </div>
    </header>
  );
};
