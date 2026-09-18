import React, { useState } from 'react';
import { Plus, RefreshCw, Check, ArrowRight } from 'lucide-react';
import { useSession } from '../context/SessionContext';

interface SessionsPageProps {
  currentSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNavigate: (tab: any) => void;
}

export const SessionsPage: React.FC<SessionsPageProps> = ({
  currentSessionId,
  onSelectSession,
  onNavigate,
}) => {
  const {
    sessions,
    loading,
    refreshSessions,
    createSession,
    selectSession: setContextSession,
  } = useSession();

  const [showModal, setShowModal] = useState(false);
  const [sessionName, setSessionName] = useState('');
  const [signerName, setSignerName] = useState('Alice_Signer');
  const [verifierName, setVerifierName] = useState('Bob_Verifier');
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setSubmitting(true);
    try {
      const newSession = await createSession(sessionName, signerName, verifierName);
      onSelectSession(newSession.id);
      setShowModal(false);
      setSessionName('');
      onNavigate('workflow');
    } catch (err: any) {
      setFormError(err.message || 'Failed to create session');
    } finally {
      setSubmitting(false);
    }
  };

  const handleRowSelect = (id: string) => {
    setContextSession(id);
    onSelectSession(id);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-100">QDS Sessions</h1>
          <p className="text-xs text-slate-400 mt-1">
            Create, inspect, and manage quantum digital signature sessions and participant credentials.
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={() => refreshSessions()}
            className="px-3 py-1.5 rounded-lg border border-zaslon-border bg-zaslon-850 hover:bg-zaslon-800 text-xs text-slate-300 flex items-center space-x-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
          <button
            onClick={() => setShowModal(true)}
            className="px-3.5 py-1.5 rounded-lg bg-zaslon-accent hover:bg-sky-500 text-xs font-semibold text-zaslon-950 flex items-center space-x-1.5 shadow"
          >
            <Plus className="w-4 h-4" />
            <span>New Session</span>
          </button>
        </div>
      </div>

      {/* Session Table */}
      <div className="rounded-xl border border-zaslon-border bg-zaslon-900/60 overflow-hidden">
        <table className="w-full text-left text-xs font-mono">
          <thead>
            <tr className="border-b border-zaslon-border bg-zaslon-850/40 text-slate-400">
              <th className="p-3.5 font-medium">Active</th>
              <th className="p-3.5 font-medium">Session ID</th>
              <th className="p-3.5 font-medium">Session Name</th>
              <th className="p-3.5 font-medium">Signer</th>
              <th className="p-3.5 font-medium">Verifier</th>
              <th className="p-3.5 font-medium">Status</th>
              <th className="p-3.5 font-medium">Created</th>
              <th className="p-3.5 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zaslon-border/40">
            {sessions.map((s) => {
              const isSelected = s.id === currentSessionId;
              return (
                <tr
                  key={s.id}
                  onClick={() => handleRowSelect(s.id)}
                  className={`hover:bg-zaslon-850/50 transition-colors cursor-pointer ${
                    isSelected ? 'bg-zaslon-800/40' : ''
                  }`}
                >
                  <td className="p-3.5">
                    {isSelected ? (
                      <span className="flex items-center justify-center w-5 h-5 rounded-full bg-zaslon-quantum/20 border border-zaslon-quantum text-zaslon-quantum">
                        <Check className="w-3 h-3" />
                      </span>
                    ) : (
                      <span className="block w-2 h-2 rounded-full bg-slate-600 ml-1.5" />
                    )}
                  </td>
                  <td className="p-3.5 text-slate-400">{s.id.substring(0, 8)}...</td>
                  <td className="p-3.5 font-medium text-slate-200">{s.session_name}</td>
                  <td className="p-3.5 text-slate-300">{s.created_by}</td>
                  <td className="p-3.5 text-slate-300">{s.verifier_id}</td>
                  <td className="p-3.5">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                        s.status === 'VERIFIED'
                          ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                          : s.status === 'REJECTED'
                          ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                          : 'bg-sky-500/20 text-sky-400 border border-sky-500/30'
                      }`}
                    >
                      {s.status}
                    </span>
                  </td>
                  <td className="p-3.5 text-slate-500">
                    {new Date(s.created_at).toLocaleString()}
                  </td>
                  <td className="p-3.5 text-right space-x-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRowSelect(s.id);
                        onNavigate('workflow');
                      }}
                      className="px-2.5 py-1 rounded bg-zaslon-800 hover:bg-zaslon-700 text-zaslon-quantum text-[11px] inline-flex items-center space-x-1"
                    >
                      <span>Pipeline</span>
                      <ArrowRight className="w-3 h-3" />
                    </button>
                  </td>
                </tr>
              );
            })}
            {sessions.length === 0 && !loading && (
              <tr>
                <td colSpan={8} className="p-8 text-center text-slate-500 font-sans">
                  No sessions found. Create a new session to initiate the QDS pipeline.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Create Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 bg-zaslon-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-zaslon-900 border border-zaslon-border rounded-xl p-6 space-y-4 shadow-xl">
            <h2 className="text-sm font-semibold text-slate-100">Create Quantum Signature Session</h2>
            {formError && (
              <div className="p-2.5 rounded bg-rose-500/10 border border-rose-500/30 text-xs text-rose-400">
                {formError}
              </div>
            )}
            <form onSubmit={handleCreate} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-400 mb-1">Session Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. SIH-26141-Research-Sig-01"
                  value={sessionName}
                  onChange={(e) => setSessionName(e.target.value)}
                  className="w-full px-3 py-2 rounded bg-zaslon-850 border border-zaslon-border text-slate-200 focus:outline-none focus:border-zaslon-accent"
                />
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Signer Identity (Alice)</label>
                <input
                  type="text"
                  required
                  value={signerName}
                  onChange={(e) => setSignerName(e.target.value)}
                  className="w-full px-3 py-2 rounded bg-zaslon-850 border border-zaslon-border text-slate-200 focus:outline-none focus:border-zaslon-accent font-mono"
                />
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Verifier Identity (Bob)</label>
                <input
                  type="text"
                  required
                  value={verifierName}
                  onChange={(e) => setVerifierName(e.target.value)}
                  className="w-full px-3 py-2 rounded bg-zaslon-850 border border-zaslon-border text-slate-200 focus:outline-none focus:border-zaslon-accent font-mono"
                />
              </div>

              <div className="flex items-center justify-end space-x-2 pt-3">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  disabled={submitting}
                  className="px-3 py-1.5 rounded border border-zaslon-border text-slate-400 hover:text-slate-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-1.5 rounded bg-zaslon-accent hover:bg-sky-500 text-zaslon-950 font-semibold font-sans disabled:opacity-50"
                >
                  {submitting ? 'Creating...' : 'Create Session'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
