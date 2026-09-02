import React from 'react';
import { LayoutDashboard, Terminal as TermIcon, Sliders, Sparkles, History, Shield, SunMoon, Command } from 'lucide-react';
import { SystemStatus, ThemeMode } from '../types/schema';

export type ActiveTab = 'dashboard' | 'studio' | 'terminal' | 'oracle' | 'history';

interface NavigationRailProps {
  activeTab: ActiveTab;
  onTabChange: (tab: ActiveTab) => void;
  status: SystemStatus | null;
  theme: ThemeMode;
  onCycleTheme: () => void;
  onOpenPalette: () => void;
  onOpenSudo: () => void;
}

export const NavigationRail: React.FC<NavigationRailProps> = ({
  activeTab,
  onTabChange,
  status,
  onCycleTheme,
  onOpenPalette,
  onOpenSudo,
}) => {
  const navItems: { id: ActiveTab; label: string; icon: React.ReactNode }[] = [
    { id: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard className="w-5 h-5" /> },
    { id: 'studio', label: 'Command Studio', icon: <Sliders className="w-5 h-5" /> },
    { id: 'terminal', label: 'Terminal HUD', icon: <TermIcon className="w-5 h-5" /> },
    { id: 'oracle', label: 'AI Oracle', icon: <Sparkles className="w-5 h-5" /> },
    { id: 'history', label: 'History Journal', icon: <History className="w-5 h-5" /> },
  ];

  return (
    <nav className="w-16 bg-surface/90 backdrop-blur-2xl border-r border-white/10 flex flex-col items-center justify-between py-4 shrink-0 z-40">
      {/* Brand Logo */}
      <div className="flex flex-col items-center gap-6">
        <button
          onClick={() => onTabChange('dashboard')}
          className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-cyan-500 flex items-center justify-center text-xl shadow-glow hover:scale-105 transition-all"
          title="Rudra Workstation"
        >
          🔱
        </button>

        {/* Navigation Icons */}
        <div className="flex flex-col items-center gap-2">
          {navItems.map(item => {
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onTabChange(item.id)}
                className={`w-11 h-11 rounded-xl flex items-center justify-center transition-all relative group ${
                  isActive
                    ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/40 shadow-glow'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.05]'
                }`}
                title={item.label}
              >
                {item.icon}
                {isActive && (
                  <span className="absolute -left-1 w-1 h-5 rounded-r-full bg-indigo-500" />
                )}
                <span className="absolute left-16 px-2.5 py-1 rounded-md bg-surface border border-white/10 text-xs font-semibold text-white whitespace-nowrap opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity z-50 shadow-xl">
                  {item.label}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Bottom Utility Actions */}
      <div className="flex flex-col items-center gap-2.5">
        <button
          onClick={onOpenPalette}
          className="w-10 h-10 rounded-xl text-slate-400 hover:text-indigo-400 hover:bg-white/[0.05] flex items-center justify-center transition-all"
          title="Command Palette (Ctrl+K)"
        >
          <Command className="w-5 h-5" />
        </button>

        <button
          onClick={onOpenSudo}
          className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all border ${
            status?.has_nopasswd_sudo
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
              : 'bg-amber-500/10 border-amber-500/30 text-amber-400 hover:border-amber-500'
          }`}
          title={status?.has_nopasswd_sudo ? 'Sudo Privileges Active' : 'Unlock Sudo Password'}
        >
          <Shield className="w-5 h-5" />
        </button>

        <button
          onClick={onCycleTheme}
          className="w-10 h-10 rounded-xl text-slate-400 hover:text-indigo-400 hover:bg-white/[0.05] flex items-center justify-center transition-all"
          title="Cycle Visual Theme"
        >
          <SunMoon className="w-5 h-5" />
        </button>
      </div>
    </nav>
  );
};
