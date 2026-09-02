import React, { useState } from 'react';
import { Sparkles, ArrowRight, Play, CheckCircle, HelpCircle } from 'lucide-react';

interface OracleViewProps {
  onExecute: (tokens: string[]) => void;
}

export const OracleView: React.FC<OracleViewProps> = ({ onExecute }) => {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState<any>(null);

  const sampleQueries = [
    'my audio is broken',
    'kill windows copilot',
    'free up disk space',
    'scan for git secret leaks',
    'diagnose network latency',
    'clean old labs and logs',
  ];

  const handleSearch = (q: string) => {
    setQuery(q);
    const lower = q.toLowerCase();
    
    if (lower.includes('audio') || lower.includes('sound') || lower.includes('driver')) {
      setResult({
        intent: 'Hardware Driver Hang / Audio Freeze',
        command: 'rudra driver doctor',
        tokens: ['rudra', 'driver', 'doctor'],
        desc: 'Scans DKMS headers, rfkill wireless blocks, PipeWire/ALSA soundcard bindings, and auto-repairs kernel modules.',
        confidence: '98%'
      });
    } else if (lower.includes('copilot') || lower.includes('recall')) {
      setResult({
        intent: 'Disable Microsoft Telemetry & AI Recall',
        command: 'rudra win copilot off',
        tokens: ['rudra', 'win', 'copilot', 'off'],
        desc: 'Applies group policy registry keys to disable Windows Copilot and telemetry data harvesting.',
        confidence: '95%'
      });
    } else if (lower.includes('disk') || lower.includes('free') || lower.includes('clean')) {
      setResult({
        intent: 'Deep System Cache & Space Optimization',
        command: 'rudra system optimize',
        tokens: ['rudra', 'system', 'optimize'],
        desc: 'Cleans package manager caches (pacman/apt), trims systemd journals, frees RAM caches, and runs SSD TRIM.',
        confidence: '94%'
      });
    } else if (lower.includes('git') || lower.includes('secret')) {
      setResult({
        intent: 'Repository Security & Secret Audit',
        command: 'rudra git audit',
        tokens: ['rudra', 'git', 'audit'],
        desc: 'Deep scans git commit history for AWS keys, private credentials, and unpushed branch safety.',
        confidence: '92%'
      });
    } else {
      setResult({
        intent: 'General System Diagnostic',
        command: 'rudra heal doctor',
        tokens: ['rudra', 'heal', 'doctor'],
        desc: 'Audits package manager locks, broken dependency keyrings, and auto-repairs system package databases.',
        confidence: '85%'
      });
    }
  };

  return (
    <div className="flex-1 p-8 overflow-y-auto max-w-4xl mx-auto w-full space-y-8">
      {/* Header */}
      <div className="border-b border-white/10 pb-6 text-center space-y-2">
        <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center text-2xl mx-auto shadow-glow">
          🔮
        </div>
        <h1 className="text-2xl font-extrabold text-white">Smart AI Oracle & Natural Language Intent</h1>
        <p className="text-xs text-slate-400 max-w-xl mx-auto">
          Describe any issue or intent in plain human language. Rudra parses your query, resolves root causes, and generates the exact diagnostic and repair command.
        </p>
      </div>

      {/* Query Input Box */}
      <div className="relative flex items-center">
        <Sparkles className="w-5 h-5 text-indigo-400 absolute left-4 pointer-events-none" />
        <input
          type="text"
          value={query}
          onChange={(e) => handleSearch(e.target.value)}
          placeholder="Ask anything, e.g. 'my audio is broken' or 'kill windows copilot'..."
          className="w-full bg-surface border border-indigo-500/30 rounded-2xl pl-12 pr-4 py-3.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 shadow-xl"
        />
      </div>

      {/* Sample Query Chips */}
      <div className="flex flex-wrap items-center justify-center gap-2">
        {sampleQueries.map((s, idx) => (
          <button
            key={idx}
            onClick={() => handleSearch(s)}
            className="px-3 py-1 rounded-full bg-white/[0.04] hover:bg-indigo-500/20 hover:text-indigo-400 border border-white/10 text-xs text-slate-400 transition-all"
          >
            {s}
          </button>
        ))}
      </div>

      {/* Diagnosis Recommendation Result Card */}
      {result && (
        <div className="p-6 rounded-2xl border border-indigo-500/40 bg-gradient-to-b from-indigo-500/10 to-transparent backdrop-blur-2xl shadow-2xl space-y-4 animate-in fade-in">
          <div className="flex items-center justify-between border-b border-white/10 pb-4">
            <div className="flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-emerald-400" />
              <h3 className="font-bold text-base text-white">{result.intent}</h3>
            </div>
            <span className="text-xs font-mono font-bold px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
              Confidence {result.confidence}
            </span>
          </div>

          <p className="text-xs text-slate-300 leading-relaxed">{result.desc}</p>

          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-2">
            <code className="px-4 py-2 rounded-xl bg-canvas border border-white/10 font-mono text-xs text-indigo-300">
              $ {result.command}
            </code>

            <button
              onClick={() => onExecute(result.tokens)}
              className="px-6 py-2.5 rounded-xl bg-indigo-500 hover:bg-indigo-600 text-white font-bold text-xs flex items-center justify-center gap-2 shadow-glow transition-all"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>Launch Fix Now</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
