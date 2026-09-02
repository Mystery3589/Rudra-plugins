import React, { useState } from 'react';
import { Search, Sliders, Play, Square, Copy, Check, Info } from 'lucide-react';
import { SchemaData, CommandSchema } from '../types/schema';

interface CommandStudioViewProps {
  schema: SchemaData | null;
  currentGroup: string;
  onSelectGroup: (g: string) => void;
  currentCmd: CommandSchema | null;
  onSelectCmd: (c: CommandSchema) => void;
  formValues: Record<string, any>;
  onParamChange: (paramName: string, val: any) => void;
  onExecute: (tokens: string[]) => void;
  isRunning: boolean;
  onAbort: () => void;
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

export const CommandStudioView: React.FC<CommandStudioViewProps> = ({
  schema,
  currentGroup,
  onSelectGroup,
  currentCmd,
  onSelectCmd,
  formValues,
  onParamChange,
  onExecute,
  isRunning,
  onAbort,
}) => {
  const [search, setSearch] = useState('');
  const [copied, setCopied] = useState(false);

  if (!schema) return null;

  const currentCommands = schema.groups[currentGroup] || [];
  const filtered = currentCommands.filter(c =>
    c.name.toLowerCase().includes(search.toLowerCase()) ||
    c.help.toLowerCase().includes(search.toLowerCase()) ||
    c.command_str.toLowerCase().includes(search.toLowerCase())
  );

  const buildCommandTokens = (): string[] => {
    if (!currentCmd) return [];
    const args = [...currentCmd.full_path];

    currentCmd.params.forEach(param => {
      const val = formValues[param.name];
      const flag = param.flags.length > 0 ? param.flags[0] : null;

      if (param.type === 'bool' || param.is_flag) {
        if (val && flag) args.push(flag);
      } else if (param.is_argument) {
        if (val !== '' && val !== undefined && val !== null) args.push(String(val));
      } else {
        if (val !== '' && val !== undefined && val !== null && flag) {
          args.push(flag);
          args.push(String(val));
        }
      }
    });

    return args;
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(buildCommandTokens().join(' '));
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Category & Command Explorer Panel */}
      <aside className="w-80 bg-surface/80 backdrop-blur-xl border-r border-white/10 flex flex-col overflow-hidden shrink-0">
        {/* Search */}
        <div className="p-3 border-b border-white/10">
          <div className="relative flex items-center">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 pointer-events-none" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Filter commands..."
              className="w-full bg-canvas/80 border border-white/10 rounded-xl pl-9 pr-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </div>
        </div>

        {/* Category Tabs */}
        <div className="p-2 flex gap-1 overflow-x-auto border-b border-white/10 scrollbar-none">
          {schema.group_names.map(g => (
            <button
              key={g}
              onClick={() => onSelectGroup(g)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap flex items-center gap-1.5 transition-all ${
                g === currentGroup
                  ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
              }`}
            >
              <span>{GROUP_ICONS[g] || '📁'}</span>
              <span>{g.toUpperCase()}</span>
            </button>
          ))}
        </div>

        {/* Commands Scrollable */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {filtered.map(cmd => {
            const isSelected = currentCmd?.command_str === cmd.command_str;
            return (
              <button
                key={cmd.command_str}
                onClick={() => onSelectCmd(cmd)}
                className={`w-full text-left p-3 rounded-xl transition-all flex flex-col gap-1 border ${
                  isSelected
                    ? 'bg-gradient-to-r from-indigo-500/20 to-cyan-500/10 border-indigo-500/40 text-slate-100 shadow-md'
                    : 'bg-transparent border-transparent text-slate-300 hover:bg-white/5 hover:border-white/5'
                }`}
              >
                <div className="flex items-center justify-between font-mono text-xs font-bold">
                  <span className={isSelected ? 'text-indigo-400' : 'text-slate-200'}>
                    {cmd.name}
                  </span>
                  {cmd.params.some(p => p.flags.includes('--dry-run')) && (
                    <span className="text-[9px] font-sans px-1.5 py-0.5 rounded bg-amber-500/10 border border-amber-500/20 text-amber-400 font-bold">
                      dry-run
                    </span>
                  )}
                </div>
                <p className="text-[11px] text-slate-400 line-clamp-1">
                  {cmd.help || 'No description provided.'}
                </p>
              </button>
            );
          })}
        </div>
      </aside>

      {/* Parameter Canvas Deck (Spacious Full Width) */}
      <main className="flex-1 p-8 overflow-y-auto flex flex-col justify-between space-y-8 max-w-5xl mx-auto w-full">
        {currentCmd && (
          <div className="space-y-6">
            {/* Hero Card */}
            <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-card-bg backdrop-blur-2xl p-6 shadow-xl">
              <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-indigo-500 via-cyan-400 to-transparent" />
              
              <div className="flex items-center gap-2 font-mono text-2xl font-extrabold tracking-tight text-white mb-2">
                <span className="text-indigo-400">$</span>
                <span>{currentCmd.command_str}</span>
              </div>
              
              <p className="text-sm text-slate-300 leading-relaxed max-w-3xl mb-4">
                {currentCmd.help || 'Configure and launch this command.'}
              </p>

              <div className="flex flex-wrap gap-2 text-xs font-mono">
                <span className="px-3 py-1 rounded-lg bg-white/5 border border-white/10 text-slate-300">
                  Group: {currentGroup}
                </span>
                <span className="px-3 py-1 rounded-lg bg-white/5 border border-white/10 text-slate-300">
                  {currentCmd.params.length} Parameters & Flags
                </span>
              </div>
            </div>

            {/* Parameters Grid */}
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-xs font-bold text-slate-400 uppercase tracking-wider">
                <Sliders className="w-3.5 h-3.5 text-indigo-400" />
                <span>Command Parameters & Customization</span>
              </div>

              {currentCmd.params.length === 0 ? (
                <div className="p-8 text-center rounded-2xl border border-dashed border-white/10 bg-card-bg/40 text-sm text-slate-400 font-mono">
                  ✓ No flags required for this command. Click Execute to launch.
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {currentCmd.params.map(param => {
                    const val = formValues[param.name];
                    const primaryFlag = param.flags.length > 0 ? param.flags[0] : param.name;

                    return (
                      <div
                        key={param.name}
                        className="p-5 rounded-2xl border border-white/10 bg-card-bg hover:bg-card-hover hover:border-indigo-500/30 transition-all shadow-md flex flex-col justify-between gap-4"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <div className="font-mono text-sm font-bold text-indigo-400 flex items-center gap-1.5">
                              <span>{primaryFlag}</span>
                              {param.required && <span className="text-rose-400">*</span>}
                            </div>
                            <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                              {param.help || (param.is_argument ? 'Positional argument' : 'Option flag')}
                            </p>
                          </div>

                          {(param.type === 'bool' || param.is_flag) && (
                            <label className="relative inline-flex items-center cursor-pointer shrink-0">
                              <input
                                type="checkbox"
                                checked={Boolean(val)}
                                onChange={(e) => onParamChange(param.name, e.target.checked)}
                                className="sr-only peer"
                              />
                              <div className="w-12 h-6 bg-white/10 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-500 peer-checked:shadow-[0_0_15px_rgba(16,185,129,0.4)]" />
                            </label>
                          )}
                        </div>

                        {param.type === 'choice' && param.choices && (
                          <div className="flex flex-wrap gap-1.5 p-1 rounded-xl bg-canvas/90 border border-white/10">
                            {param.choices.map(c => (
                              <button
                                key={c}
                                type="button"
                                onClick={() => onParamChange(param.name, c)}
                                className={`px-3 py-1.5 rounded-lg text-xs font-mono font-semibold transition-all ${
                                  val === c
                                    ? 'bg-indigo-500 text-white shadow-md'
                                    : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
                                }`}
                              >
                                {c}
                              </button>
                            ))}
                          </div>
                        )}

                        {(param.type === 'int' || param.type === 'float') && (
                          <input
                            type="number"
                            value={val !== undefined && val !== null ? val : ''}
                            onChange={(e) => onParamChange(param.name, e.target.value === '' ? '' : Number(e.target.value))}
                            placeholder={param.required ? 'Required number' : 'Optional number'}
                            className="w-full bg-canvas/90 border border-white/10 rounded-xl px-4 py-2 text-xs text-slate-100 font-mono placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                          />
                        )}

                        {param.type !== 'bool' && !param.is_flag && param.type !== 'choice' && param.type !== 'int' && param.type !== 'float' && (
                          <input
                            type="text"
                            value={val || ''}
                            onChange={(e) => onParamChange(param.name, e.target.value)}
                            placeholder={param.required ? 'Required value' : 'Optional value...'}
                            className="w-full bg-canvas/90 border border-white/10 rounded-xl px-4 py-2 text-xs text-slate-100 font-mono placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                          />
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Sticky Live Syntax Run Deck */}
        <div className="sticky bottom-0 pt-4">
          <div className="p-4 rounded-2xl border border-white/10 bg-card-bg/95 backdrop-blur-2xl shadow-2xl flex items-center justify-between gap-4">
            <div className="flex-1 bg-canvas border border-white/10 rounded-xl px-4 py-3 font-mono text-xs overflow-x-auto whitespace-nowrap flex items-center justify-between gap-3">
              <div className="flex items-center gap-1.5">
                <span className="text-indigo-400 font-bold">$ rudra</span>
                {buildCommandTokens().slice(1).map((tok, idx) => (
                  <span key={idx} className={tok.startsWith('-') ? 'text-amber-400' : 'text-slate-200'}>
                    {tok}
                  </span>
                ))}
              </div>

              <button
                onClick={handleCopy}
                className="text-slate-400 hover:text-indigo-400 transition-colors shrink-0 p-1.5 rounded hover:bg-white/5"
                title="Copy command"
              >
                {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
              </button>
            </div>

            {isRunning ? (
              <button
                onClick={onAbort}
                className="px-8 py-3 rounded-xl bg-rose-500 hover:bg-rose-600 text-white font-bold text-xs flex items-center gap-2 shadow-lg shadow-rose-500/30 transition-all"
              >
                <Square className="w-4 h-4 fill-current" />
                <span>STOP</span>
              </button>
            ) : (
              <button
                onClick={() => onExecute(buildCommandTokens())}
                className="px-8 py-3 rounded-xl bg-gradient-to-r from-indigo-500 via-indigo-600 to-cyan-500 hover:from-indigo-400 hover:to-cyan-400 text-white font-extrabold text-xs flex items-center gap-2 shadow-glow hover:scale-105 transition-all"
              >
                <Play className="w-4 h-4 fill-current" />
                <span>EXECUTE</span>
              </button>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};
