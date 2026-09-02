import React, { useState } from 'react';
import { Shield, X, KeyRound } from 'lucide-react';

interface SudoModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const SudoModal: React.FC<SudoModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!password) return;
    setLoading(true);
    setError('');

    try {
      const res = await fetch('/api/sudo-auth', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password })
      });

      if (res.ok) {
        onSuccess();
        onClose();
      } else {
        setError('Authentication failed. Invalid password.');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to authenticate');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      onClick={onClose}
      className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-md bg-surface border border-amber-500/30 rounded-2xl p-6 shadow-2xl shadow-amber-500/10 flex flex-col gap-4"
      >
        <div className="flex items-center justify-between border-b border-white/10 pb-3">
          <div className="flex items-center gap-2 text-sm font-bold text-amber-400">
            <Shield className="w-5 h-5" />
            <span>Sudo Privilege Elevation</span>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-200">
            <X className="w-4 h-4" />
          </button>
        </div>

        <p className="text-xs text-slate-300 leading-relaxed">
          Enter your administrative root / sudo password. It is cached in RAM memory only for the current active session and is <strong>never written to disk</strong>.
        </p>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="relative flex items-center">
            <KeyRound className="w-4 h-4 text-slate-500 absolute left-3.5 pointer-events-none" />
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter sudo password..."
              autoFocus
              className="w-full bg-canvas border border-white/10 rounded-xl pl-10 pr-4 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500 transition-all"
            />
          </div>

          {error && <p className="text-xs text-rose-400 font-medium">{error}</p>}

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-xs font-semibold text-slate-400 hover:text-slate-200 hover:bg-white/5"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-5 py-2 rounded-lg bg-amber-500 hover:bg-amber-600 text-black font-bold text-xs transition-all shadow-md shadow-amber-500/20 disabled:opacity-50"
            >
              {loading ? 'Validating...' : 'Unlock Sudo'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
