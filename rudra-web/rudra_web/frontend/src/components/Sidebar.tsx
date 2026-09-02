import React from 'react';
import { Search } from 'lucide-react';
import { SchemaData, CommandSchema } from '../types/schema';

interface SidebarProps {
  schema: SchemaData | null;
  currentGroup: string;
  currentCmd: CommandSchema | null;
  onSelectGroup: (group: string) => void;
  onSelectCmd: (cmd: CommandSchema) => void;
  searchQuery: string;
  onSearchChange: (q: string) => void;
}

const GROUP_ICONS: Record<string, string> = {
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

export const Sidebar: React.FC<SidebarProps> = ({
  schema,
  currentGroup,
  currentCmd,
  onSelectGroup,
  onSelectCmd,
  searchQuery,
  onSearchChange
}) => {
  if (!schema) return null;

  const currentCommands = schema.groups[currentGroup] || [];
  const filtered = currentCommands.filter(c =>
    c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    c.help.toLowerCase().includes(searchQuery.toLowerCase()) ||
    c.command_str.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <aside className="w-72 bg-surface/60 backdrop-blur-xl border-r border-white/10 flex flex-col overflow-hidden shrink-0">
      <div className="p-3 border-b border-white/10">
        <div className="relative flex items-center">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search commands..."
            className="w-full bg-canvas/80 border border-white/10 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all"
          />
        </div>
      </div>

      <div className="px-2 py-2 flex gap-1.5 overflow-x-auto border-b border-white/10 scrollbar-none">
        {schema.group_names.map(g => (
          <button
            key={g}
            onClick={() => onSelectGroup(g)}
            className={`px-2.5 py-1 rounded-md text-xs font-semibold whitespace-nowrap flex items-center gap-1.5 transition-all ${
              g === currentGroup
                ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
            }`}
          >
            <span>{GROUP_ICONS[g] || '📁'}</span>
            <span>{g.toUpperCase()}</span>
          </button>
        ))}
      </div>

      <div className="px-3 py-2 flex items-center justify-between text-[11px] font-bold tracking-wider text-slate-500 uppercase">
        <span>{currentGroup} COMMANDS</span>
        <span className="px-1.5 py-0.5 rounded bg-white/5 text-slate-400 font-mono text-[10px]">
          {filtered.length}
        </span>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {filtered.map(cmd => {
          const isSelected = currentCmd?.command_str === cmd.command_str;
          return (
            <button
              key={cmd.command_str}
              onClick={() => onSelectCmd(cmd)}
              className={`w-full text-left p-2.5 rounded-lg transition-all flex flex-col gap-1 border ${
                isSelected
                  ? 'bg-gradient-to-r from-indigo-500/15 to-cyan-500/10 border-indigo-500/40 text-slate-100 shadow-[0_0_15px_rgba(99,102,241,0.15)]'
                  : 'bg-transparent border-transparent text-slate-300 hover:bg-white/[0.04] hover:border-white/5'
              }`}
            >
              <div className="flex items-center justify-between font-mono text-xs font-bold">
                <span className={isSelected ? 'text-indigo-400' : 'text-slate-200'}>
                  {cmd.name}
                </span>
                {cmd.params.some(p => p.flags.includes('--dry-run')) && (
                  <span className="text-[9px] font-sans px-1.5 py-0.5 rounded bg-amber-500/10 border border-amber-500/20 text-amber-400">
                    dry-run
                  </span>
                )}
              </div>
              <p className="text-[11px] text-slate-400 line-clamp-1 font-sans">
                {cmd.help || 'No description'}
              </p>
            </button>
          );
        })}
      </div>
    </aside>
  );
};
