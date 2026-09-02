import React from 'react';
import { Sliders } from 'lucide-react';
import { CommandSchema } from '../types/schema';

interface ParameterFormProps {
  cmd: CommandSchema;
  values: Record<string, any>;
  onChange: (paramName: string, value: any) => void;
}

export const ParameterForm: React.FC<ParameterFormProps> = ({ cmd, values, onChange }) => {
  return (
    <div className="space-y-4">
      <div className="relative overflow-hidden rounded-xl border border-white/10 bg-card-bg backdrop-blur-xl p-5 shadow-xl transition-all hover:border-white/20">
        <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-indigo-500 via-cyan-400 to-transparent" />
        
        <div className="flex items-center gap-2 mb-2 font-mono text-xl font-extrabold tracking-tight text-white">
          <span className="text-indigo-400">$</span>
          <span>{cmd.command_str}</span>
        </div>
        
        <p className="text-sm text-slate-300 leading-relaxed max-w-3xl mb-4">
          {cmd.help || 'Execute command across your infrastructure.'}
        </p>

        <div className="flex flex-wrap gap-2 text-xs font-mono">
          <span className="px-2.5 py-1 rounded-md bg-white/5 border border-white/10 text-slate-400">
            Path: {cmd.full_path.join(' ')}
          </span>
          <span className="px-2.5 py-1 rounded-md bg-white/5 border border-white/10 text-slate-400">
            {cmd.params.length} Parameter{cmd.params.length === 1 ? '' : 's'}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-2 text-xs font-bold text-slate-400 uppercase tracking-wider">
        <Sliders className="w-3.5 h-3.5 text-indigo-400" />
        <span>Execution Parameters & Options</span>
      </div>

      {cmd.params.length === 0 ? (
        <div className="p-8 text-center rounded-xl border border-dashed border-white/10 bg-card-bg/40 text-sm text-slate-400 font-mono">
          ✓ No parameters required for this command. Ready to execute.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
          {cmd.params.map(param => {
            const val = values[param.name];
            const primaryFlag = param.flags.length > 0 ? param.flags[0] : param.name;

            return (
              <div
                key={param.name}
                className="p-4 rounded-xl border border-white/10 bg-card-bg/70 hover:bg-card-hover hover:border-indigo-500/30 transition-all shadow-md flex flex-col justify-between gap-3 group"
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="font-mono text-xs font-bold text-indigo-400 flex items-center gap-1.5">
                      <span>{primaryFlag}</span>
                      {param.required && <span className="text-rose-400">*</span>}
                    </div>
                    <p className="text-xs text-slate-400 mt-1 leading-snug">
                      {param.help || (param.is_argument ? 'Command argument' : 'Option flag')}
                    </p>
                  </div>

                  {(param.type === 'bool' || param.is_flag) && (
                    <label className="relative inline-flex items-center cursor-pointer shrink-0">
                      <input
                        type="checkbox"
                        checked={Boolean(val)}
                        onChange={(e) => onChange(param.name, e.target.checked)}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-white/10 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-500 peer-checked:shadow-[0_0_12px_rgba(16,185,129,0.4)]" />
                    </label>
                  )}
                </div>

                {param.type === 'choice' && param.choices && (
                  <div className="flex flex-wrap gap-1.5 p-1 rounded-lg bg-canvas/80 border border-white/10">
                    {param.choices.map(c => (
                      <button
                        key={c}
                        type="button"
                        onClick={() => onChange(param.name, c)}
                        className={`px-2.5 py-1 rounded-md text-xs font-mono transition-all ${
                          val === c
                            ? 'bg-indigo-500 text-white font-bold shadow-sm'
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
                    onChange={(e) => onChange(param.name, e.target.value === '' ? '' : Number(e.target.value))}
                    placeholder={param.required ? 'Required number' : 'Optional number'}
                    className="w-full bg-canvas/80 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-slate-100 font-mono placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all"
                  />
                )}

                {param.type !== 'bool' && !param.is_flag && param.type !== 'choice' && param.type !== 'int' && param.type !== 'float' && (
                  <input
                    type="text"
                    value={val || ''}
                    onChange={(e) => onChange(param.name, e.target.value)}
                    placeholder={param.required ? 'Required value' : 'Optional value...'}
                    className="w-full bg-canvas/80 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-slate-100 font-mono placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all"
                  />
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
