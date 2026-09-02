import React from 'react';
import { Cpu, HardDrive, ShieldCheck, Zap, Wrench, ShieldAlert, Sparkles, Box, Play, Sliders } from 'lucide-react';
import { SystemStatus } from '../types/schema';

interface DashboardViewProps {
  status: SystemStatus | null;
  onExecute: (tokens: string[]) => void;
  onNavigateTab: (tab: any) => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({ status, onExecute, onNavigateTab }) => {
  const quickWorkflows = [
    {
      title: 'Full System Health & Optimize',
      desc: 'Clean package caches, trim journal logs, purge temp dirs, and flush RAM.',
      tokens: ['rudra', 'system', 'optimize', '--dry-run'],
      icon: <Zap className="w-6 h-6 text-indigo-400" />,
      tag: 'RECOMMENDED',
      color: 'from-indigo-500/20 via-indigo-500/5 to-transparent border-indigo-500/30'
    },
    {
      title: 'Hardware Driver Doctor',
      desc: 'Auto-diagnose kernel modules, GPU conflicts, and audio DSP hangs.',
      tokens: ['rudra', 'driver', 'doctor'],
      icon: <Wrench className="w-6 h-6 text-cyan-400" />,
      tag: 'DIAGNOSTIC',
      color: 'from-cyan-500/20 via-cyan-500/5 to-transparent border-cyan-500/30'
    },
    {
      title: 'Git Security & Repo Audit',
      desc: 'Scan repository for committed secrets, tokens, and prune stale branches.',
      tokens: ['rudra', 'git', 'audit'],
      icon: <ShieldAlert className="w-6 h-6 text-emerald-400" />,
      tag: 'SECURITY',
      color: 'from-emerald-500/20 via-emerald-500/5 to-transparent border-emerald-500/30'
    },
    {
      title: 'Disposable Lab Environment',
      desc: 'Spin up an isolated sandbox to test unverified packages safely.',
      tokens: ['rudra', 'lab', 'cleanup'],
      icon: <Box className="w-6 h-6 text-purple-400" />,
      tag: 'SANDBOX',
      color: 'from-purple-500/20 via-purple-500/5 to-transparent border-purple-500/30'
    },
  ];

  return (
    <div className="flex-1 p-8 overflow-y-auto space-y-8 max-w-7xl mx-auto w-full">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/10 pb-6">
        <div>
          <h1 className="text-2xl font-extrabold text-white tracking-tight flex items-center gap-3">
            <span>Rudra Command Center</span>
            <span className="text-xs font-mono px-2.5 py-0.5 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-400">
              OPERATIONAL
            </span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Autonomous multi-platform system optimizer, driver orchestrator, and sandbox laboratory.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => onNavigateTab('studio')}
            className="px-4 py-2 rounded-xl bg-indigo-500 hover:bg-indigo-600 text-white text-xs font-bold transition-all shadow-glow flex items-center gap-2"
          >
            <Sliders className="w-4 h-4" />
            <span>Open Command Studio</span>
          </button>
        </div>
      </div>

      {/* Telemetry Vitals Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-2xl bg-card-bg border border-white/10 backdrop-blur-xl shadow-lg flex items-center justify-between">
          <div>
            <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">OS Platform</div>
            <div className="text-lg font-mono font-extrabold text-white mt-1">{status?.os || 'Linux'}</div>
            <div className="text-[11px] font-mono text-slate-400">{status?.platform_release || '7.2.2-cachyos'}</div>
          </div>
          <div className="w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
            <Cpu className="w-6 h-6" />
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-card-bg border border-white/10 backdrop-blur-xl shadow-lg flex items-center justify-between">
          <div>
            <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">Architecture</div>
            <div className="text-lg font-mono font-extrabold text-cyan-400 mt-1">{status?.machine || 'x86_64'}</div>
            <div className="text-[11px] text-slate-400">64-Bit Standard</div>
          </div>
          <div className="w-12 h-12 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
            <HardDrive className="w-6 h-6" />
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-card-bg border border-white/10 backdrop-blur-xl shadow-lg flex items-center justify-between">
          <div>
            <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">Privilege Mode</div>
            <div className="text-lg font-mono font-extrabold text-emerald-400 mt-1">
              {status?.has_nopasswd_sudo ? 'NOPASSWD' : 'RAM Sudo'}
            </div>
            <div className="text-[11px] text-slate-400">Elevated Operations</div>
          </div>
          <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
            <ShieldCheck className="w-6 h-6" />
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-card-bg border border-white/10 backdrop-blur-xl shadow-lg flex items-center justify-between">
          <div>
            <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">Workstation Engine</div>
            <div className="text-lg font-mono font-extrabold text-purple-400 mt-1">Ready</div>
            <div className="text-[11px] text-slate-400">Daemon Active</div>
          </div>
          <div className="w-12 h-12 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
            <Sparkles className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* 1-Click Launchpad Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
            <Zap className="w-4 h-4 text-indigo-400" />
            <span>1-Click Launchpad Workflows</span>
          </h2>
          <span className="text-xs text-slate-500 font-mono">Quick triggers with preset arguments</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {quickWorkflows.map((wf, idx) => (
            <div
              key={idx}
              className={`p-6 rounded-2xl border bg-card-bg/80 backdrop-blur-xl hover:bg-card-hover transition-all flex flex-col justify-between gap-4 relative overflow-hidden group shadow-lg ${wf.color}`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-center gap-3.5">
                  <div className="p-3 rounded-xl bg-white/[0.04] border border-white/10">
                    {wf.icon}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-bold text-base text-white group-hover:text-indigo-400 transition-colors">
                        {wf.title}
                      </h3>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-white/10 text-slate-300 font-bold">
                        {wf.tag}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                      {wf.desc}
                    </p>
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-between pt-2 border-t border-white/5">
                <code className="text-xs font-mono text-indigo-300 bg-canvas/80 px-3 py-1 rounded-lg border border-white/5">
                  $ {wf.tokens.join(' ')}
                </code>

                <button
                  onClick={() => onExecute(wf.tokens)}
                  className="px-4 py-1.5 rounded-xl bg-white/[0.08] hover:bg-indigo-500 hover:text-white text-slate-200 text-xs font-bold transition-all flex items-center gap-1.5"
                >
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span>Run Now</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
