import React, { useEffect, useState } from 'react';
import { History, Trash2, Copy, Check, ArrowLeft } from 'lucide-react';
import { HistoryRecord } from '../types/schema';

interface HistoryViewProps {
  onBack: () => void;
  onReRun: (args: string[]) => void;
}

export const HistoryView: React.FC<HistoryViewProps> = ({ onBack, onReRun }) => {
  const [history, setHistory] = useState<HistoryRecord[]>([]);
  const [search, setSearch] = useState('');
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const fetchHistory = async () => {
    try {
      const res = await fetch('/api/history');
      const data = await res.json();
      setHistory(data);
    } catch (err) {
      console.error('Failed to fetch history:', err);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const handleClear = async () => {
    if (!confirm('Clear all execution history?')) return;
    try {
      await fetch('/api/history', { method: 'DELETE' });
      setHistory([]);
    } catch (err) {
      console.error(err);
    }
  };

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 1500);
  };

  const filtered = history.filter(h =>
    h.command.toLowerCase().includes(search.toLowerCase()) ||
    h.timestamp.includes(search)
  );

  return (
    <div className="flex-1 p-8 overflow-y-auto max-w-5xl mx-auto w-full space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <h1 className="text-xl font-bold text-white flex items-center gap-2">
              <History className="w-5 h-5 text-indigo-400" />
              <span>Execution Journal</span>
            </h1>
            <p className="text-xs text-slate-400">
              Retains up to 100 recent executions within the last 7 days.
            </p>
          </div>
        </div>

        <button
          onClick={handleClear}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-rose-500/30 bg-rose-500/10 text-rose-400 hover:bg-rose-500/20 text-xs font-semibold"
        >
          <Trash2 className="w-3.5 h-3.5" />
          <span>Clear History</span>
        </button>
      </div>

      <input
        type="text"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Filter history records..."
        className="w-full bg-surface border border-white/10 rounded-xl px-4 py-2.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
      />

      <div className="rounded-xl border border-white/10 bg-surface overflow-hidden shadow-xl">
        <table className="w-full text-left text-xs">
          <thead className="bg-white/[0.02] border-b border-white/10 text-slate-400 font-mono">
            <tr>
              <th className="p-3.5">TIME</th>
              <th className="p-3.5">COMMAND</th>
              <th className="p-3.5">DURATION</th>
              <th className="p-3.5">STATUS</th>
              <th className="p-3.5 text-right">ACTION</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5 font-mono">
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={5} className="p-8 text-center text-slate-500">
                  No execution records found.
                </td>
              </tr>
            ) : (
              filtered.map(item => {
                const isOk = item.exit_code === 0;
                return (
                  <tr key={item.id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="p-3.5 text-slate-400">{item.timestamp}</td>
                    <td className="p-3.5 text-indigo-300 font-semibold">$ {item.command}</td>
                    <td className="p-3.5 text-slate-400">{item.duration_sec}s</td>
                    <td className="p-3.5">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        isOk ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                      }`}>
                        {isOk ? 'EXIT 0' : `EXIT ${item.exit_code}`}
                      </span>
                    </td>
                    <td className="p-3.5 text-right space-x-2">
                      <button
                        onClick={() => handleCopy(item.id, item.command)}
                        className="p-1.5 rounded hover:bg-white/5 text-slate-400 hover:text-slate-200"
                        title="Copy command"
                      >
                        {copiedId === item.id ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
