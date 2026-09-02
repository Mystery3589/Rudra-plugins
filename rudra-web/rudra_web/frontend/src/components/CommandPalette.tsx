import React, { useState } from 'react';
import { Search, Command, X } from 'lucide-react';
import { SchemaData, CommandSchema } from '../types/schema';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  schema: SchemaData | null;
  onSelectCmd: (group: string, cmd: CommandSchema) => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  onClose,
  schema,
  onSelectCmd
}) => {
  const [query, setQuery] = useState('');

  if (!isOpen || !schema) return null;

  const allCommands: { group: string; cmd: CommandSchema }[] = [];
  schema.group_names.forEach(g => {
    const list = schema.groups[g] || [];
    list.forEach(c => allCommands.push({ group: g, cmd: c }));
  });

  const matches = allCommands.filter(({ group, cmd }) =>
    cmd.name.toLowerCase().includes(query.toLowerCase()) ||
    cmd.help.toLowerCase().includes(query.toLowerCase()) ||
    cmd.command_str.toLowerCase().includes(query.toLowerCase())
  ).slice(0, 8);

  return (
    <div
      onClick={onClose}
      className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-xl bg-surface border border-indigo-500/30 rounded-2xl p-4 shadow-2xl shadow-indigo-500/20 flex flex-col gap-3"
      >
        <div className="flex items-center justify-between border-b border-white/10 pb-3">
          <div className="flex items-center gap-2 text-sm font-bold text-slate-200">
            <Command className="w-4 h-4 text-indigo-400" />
            <span>Command Palette</span>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-200">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="relative flex items-center">
          <Search className="w-4 h-4 text-slate-500 absolute left-3.5 pointer-events-none" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type a command name or keyword..."
            autoFocus
            className="w-full bg-canvas border border-white/10 rounded-xl pl-10 pr-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all"
          />
        </div>

        <div className="space-y-1 max-h-80 overflow-y-auto">
          {matches.map(({ group, cmd }) => (
            <button
              key={cmd.command_str}
              onClick={() => {
                onSelectCmd(group, cmd);
                onClose();
              }}
              className="w-full text-left p-3 rounded-xl hover:bg-white/5 border border-transparent hover:border-white/10 transition-all flex items-center justify-between group"
            >
              <div>
                <div className="font-mono text-xs font-bold text-slate-200 group-hover:text-indigo-400">
                  {cmd.command_str}
                </div>
                <div className="text-[11px] text-slate-400 line-clamp-1">{cmd.help}</div>
              </div>
              <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-white/5 text-slate-400">
                {group}
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
