import React from 'react';
import { Play, Square, Copy, Check } from 'lucide-react';

interface ControlDeckProps {
  commandTokens: string[];
  isRunning: boolean;
  onExecute: () => void;
  onAbort: () => void;
  onCopy: () => void;
  isCopied: boolean;
}

export const ControlDeck: React.FC<ControlDeckProps> = ({
  commandTokens,
  isRunning,
  onExecute,
  onAbort,
  onCopy,
  isCopied
}) => {
  return (
    <div className="mt-auto pt-4">
      <div className="p-3 rounded-xl border border-white/10 bg-card-bg backdrop-blur-xl shadow-xl flex items-center justify-between gap-4">
        {/* Tokenized Syntax Preview Box */}
        <div className="flex-1 bg-canvas/90 border border-white/10 rounded-lg px-4 py-2.5 font-mono text-xs overflow-x-auto whitespace-nowrap flex items-center justify-between gap-3">
          <div className="flex items-center gap-1.5">
            <span className="text-indigo-400 font-bold">$ rudra</span>
            {commandTokens.slice(1).map((tok, idx) => {
              if (tok.startsWith('-')) {
                return <span key={idx} className="text-amber-400">{tok}</span>;
              }
              if (idx === 0) {
                return <span key={idx} className="text-cyan-400 font-semibold">{tok}</span>;
              }
              if (idx === 1 && !tok.startsWith('-')) {
                return <span key={idx} className="text-emerald-400 font-semibold">{tok}</span>;
              }
              return <span key={idx} className="text-slate-200">{tok}</span>;
            })}
          </div>

          <button
            onClick={onCopy}
            className="text-slate-400 hover:text-indigo-400 transition-colors shrink-0 p-1 rounded hover:bg-white/5"
            title="Copy command"
          >
            {isCopied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          </button>
        </div>

        {/* Action Button */}
        {isRunning ? (
          <button
            onClick={onAbort}
            className="px-6 py-2.5 rounded-lg bg-rose-500 hover:bg-rose-600 text-white font-bold text-xs flex items-center gap-2 shadow-lg shadow-rose-500/20 transition-all"
          >
            <Square className="w-3.5 h-3.5 fill-current" />
            <span>STOP</span>
          </button>
        ) : (
          <button
            onClick={onExecute}
            className="px-6 py-2.5 rounded-lg bg-gradient-to-r from-indigo-500 via-indigo-600 to-cyan-500 hover:from-indigo-400 hover:to-cyan-400 text-white font-bold text-xs flex items-center gap-2 shadow-lg shadow-indigo-500/25 transition-all hover:scale-[1.02]"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>EXECUTE</span>
          </button>
        )}
      </div>
    </div>
  );
};
