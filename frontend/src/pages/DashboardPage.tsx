import React, { useEffect, useState } from 'react';
import {
  Layers,
  ShieldAlert,
  CheckCircle2,
  Radio,
  ArrowUpRight,
  Play,
  ShieldCheck,
  Zap,
  Activity,
} from 'lucide-react';
import { api } from '../services/api';
import { AuditEvent } from '../types';
import { useSession } from '../context/SessionContext';

interface DashboardPageProps {
  onSelectSession: (sessionId: string) => void;
  onNavigate: (tab: any) => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({ onSelectSession, onNavigate }) => {
  const { sessions, currentSession, selectSession } = useSession();
  const [recentAudits, setRecentAudits] = useState<AuditEvent[]>([]);
  const [loadingAudits, setLoadingAudits] = useState(false);

  useEffect(() => {
    const loadAudits = async () => {
      setLoadingAudits(true);
      try {
        const auditData = await api.getAuditTrail(undefined, 8);
        setRecentAudits(auditData);
      } catch (err) {
        console.error('Failed to load audit stream:', err);
      } finally {
        setLoadingAudits(false);
      }
    };
    loadAudits();
  }, []);

  const totalSessions = sessions.length;
  const verifiedCount = sessions.filter((s) => s.status === 'VERIFIED').length;
  const rejectedCount = sessions.filter((s) => s.status === 'REJECTED').length;
  const totalOperations = sessions.length * 4096;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-100">Cybersecurity Research Dashboard</h1>
          <p className="text-xs text-slate-400 mt-1">
            Quantum-Teleportation-Based Cyber Threat Detection for Quantum Digital Signatures (SIH 26141)
          </p>
        </div>
        <button
          onClick={() => onNavigate('sessions')}
          className="px-3.5 py-1.5 rounded-lg bg-zaslon-accent hover:bg-sky-500 text-xs font-semibold text-zaslon-950 flex items-center space-x-1.5 shadow"
        >
          <span>Manage Sessions</span>
          <ArrowUpRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-zaslon-900/60 border border-zaslon-border">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase text-slate-400">Total Sessions</span>
            <Layers className="w-4 h-4 text-zaslon-quantum" />
          </div>
          <div className="text-2xl font-bold font-mono text-slate-100 mt-2">{totalSessions}</div>
          <div className="text-[11px] text-slate-500 mt-1">Managed QDS Workflows</div>
        </div>

        <div className="p-4 rounded-xl bg-zaslon-900/60 border border-zaslon-border">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase text-slate-400">Verified Signatures</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-emerald-400 mt-2">{verifiedCount}</div>
          <div className="text-[11px] text-slate-500 mt-1">Fisher Test Validated</div>
        </div>

        <div className="p-4 rounded-xl bg-zaslon-900/60 border border-zaslon-border">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase text-slate-400">Detected Threats</span>
            <ShieldAlert className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-rose-400 mt-2">{rejectedCount}</div>
          <div className="text-[11px] text-slate-500 mt-1">Attacks Flagged by Rules</div>
        </div>

        <div className="p-4 rounded-xl bg-zaslon-900/60 border border-zaslon-border">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase text-slate-400">Quantum Ops Workload</span>
            <Radio className="w-4 h-4 text-sky-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-sky-400 mt-2">
            {totalOperations.toLocaleString()}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">4,096 3-Qubit Circuits / Session</div>
        </div>
      </div>

      {/* Active Session Overview Card */}
      {currentSession && (
        <div className="p-5 rounded-xl bg-zaslon-900/70 border border-zaslon-accent/40 shadow-sm space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center space-x-2.5">
              <div className="w-2.5 h-2.5 rounded-full bg-zaslon-quantum animate-pulse" />
              <h2 className="text-sm font-semibold text-slate-200">
                Active Session: <span className="text-zaslon-quantum font-mono">{currentSession.session_name}</span>
              </h2>
              <span
                className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold ${
                  currentSession.status === 'VERIFIED'
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    : currentSession.status === 'REJECTED'
                    ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                    : 'bg-sky-500/20 text-sky-400 border border-sky-500/30'
                }`}
              >
                {currentSession.status}
              </span>
            </div>

            <div className="flex items-center space-x-2">
              <button
                onClick={() => onNavigate('workflow')}
                className="px-3 py-1.5 rounded-lg bg-zaslon-800 hover:bg-zaslon-700 text-xs text-zaslon-quantum font-medium flex items-center space-x-1.5 border border-zaslon-border"
              >
                <Play className="w-3.5 h-3.5" />
                <span>Open Pipeline</span>
              </button>
              <button
                onClick={() => onNavigate('teleportation')}
                className="px-3 py-1.5 rounded-lg bg-zaslon-800 hover:bg-zaslon-700 text-xs text-slate-300 font-medium flex items-center space-x-1.5 border border-zaslon-border"
              >
                <Zap className="w-3.5 h-3.5 text-amber-400" />
                <span>Teleportation</span>
              </button>
              <button
                onClick={() => onNavigate('verification')}
                className="px-3 py-1.5 rounded-lg bg-zaslon-800 hover:bg-zaslon-700 text-xs text-slate-300 font-medium flex items-center space-x-1.5 border border-zaslon-border"
              >
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                <span>Verification</span>
              </button>
              <button
                onClick={() => onNavigate('attacks')}
                className="px-3 py-1.5 rounded-lg bg-zaslon-800 hover:bg-zaslon-700 text-xs text-rose-300 font-medium flex items-center space-x-1.5 border border-zaslon-border"
              >
                <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
                <span>Threat Simulator</span>
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs font-mono pt-2 border-t border-zaslon-border/50 text-slate-400">
            <div>
              Signer: <span className="text-slate-200 font-semibold">{currentSession.created_by}</span>
            </div>
            <div>
              Verifier: <span className="text-slate-200 font-semibold">{currentSession.verifier_id}</span>
            </div>
            <div>
              Created:{' '}
              <span className="text-slate-300">
                {new Date(currentSession.created_at).toLocaleString()}
              </span>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Active Sessions */}
        <div className="lg:col-span-2 p-5 rounded-xl bg-zaslon-900/60 border border-zaslon-border">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-slate-200">Recent QDS Sessions</h3>
            <button
              onClick={() => onNavigate('sessions')}
              className="text-xs text-zaslon-quantum hover:underline flex items-center"
            >
              View All <ArrowUpRight className="w-3 h-3 ml-0.5" />
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead>
                <tr className="border-b border-zaslon-border text-slate-400">
                  <th className="pb-2 font-medium">Session Name</th>
                  <th className="pb-2 font-medium">Signer</th>
                  <th className="pb-2 font-medium">Verifier</th>
                  <th className="pb-2 font-medium">Status</th>
                  <th className="pb-2 font-medium text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zaslon-border/50">
                {sessions.slice(0, 8).map((s) => (
                  <tr
                    key={s.id}
                    className={`hover:bg-zaslon-850/50 ${
                      currentSession?.id === s.id ? 'bg-zaslon-850/30' : ''
                    }`}
                  >
                    <td className="py-2.5 font-medium text-slate-200">{s.session_name}</td>
                    <td className="py-2.5 text-slate-400">{s.created_by}</td>
                    <td className="py-2.5 text-slate-400">{s.verifier_id}</td>
                    <td className="py-2.5">
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
                    <td className="py-2.5 text-right space-x-2">
                      <button
                        onClick={() => {
                          selectSession(s.id);
                          onSelectSession(s.id);
                          onNavigate('workflow');
                        }}
                        className="text-xs text-zaslon-quantum hover:text-sky-300"
                      >
                        Select
                      </button>
                    </td>
                  </tr>
                ))}
                {sessions.length === 0 && (
                  <tr>
                    <td colSpan={5} className="py-6 text-center text-slate-500">
                      No sessions created yet. Create a session to begin.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Security Audit Feed */}
        <div className="p-5 rounded-xl bg-zaslon-900/60 border border-zaslon-border">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-slate-200">Security Audit Stream</h3>
            <button
              onClick={() => onNavigate('audit')}
              className="text-xs text-slate-400 hover:text-slate-200 flex items-center space-x-1"
            >
              <span>Full Log</span>
              <Activity className="w-3 h-3 text-zaslon-quantum" />
            </button>
          </div>

          <div className="space-y-3">
            {recentAudits.map((a) => (
              <div key={a.id} className="p-2.5 rounded bg-zaslon-850/50 border border-zaslon-border text-xs">
                <div className="flex items-center justify-between font-mono">
                  <span className="font-semibold text-slate-300 text-[11px]">{a.event_type}</span>
                  <span className="text-[10px] text-slate-500">
                    {new Date(a.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                <div className="text-[11px] text-slate-400 mt-1">
                  Actor: <span className="font-mono text-slate-300">{a.actor}</span>
                </div>
              </div>
            ))}
            {recentAudits.length === 0 && !loadingAudits && (
              <div className="text-center py-6 text-xs text-slate-500">
                Audit stream empty.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
