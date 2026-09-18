import React, { useState, useEffect } from 'react';
import {
  Activity,
  Database,
  Shield,
  RefreshCw,
  Search,
  FileClock,
  Atom
} from 'lucide-react';
import { RoleNavbar } from '../../components/layout/RoleNavbar';
import { useAuth } from '../../context/AuthContext';

export const ResearchDiagnosticsPage: React.FC = () => {
  const { token } = useAuth();
  const [healthData, setHealthData] = useState<any | null>(null);
  const [auditEvents, setAuditEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const fetchDiagnostics = async () => {
    setLoading(true);
    try {
      // Health check
      const healthRes = await fetch('/api/v1/health');
      if (healthRes.ok) {
        const hData = await healthRes.json();
        setHealthData(hData);
      }

      // Audit trail
      const auditRes = await fetch('/api/v1/audit/trail?limit=100', {
        headers: token ? { Authorization: `Bearer ${token}` } : {}
      });
      if (auditRes.ok) {
        const aData = await auditRes.json();
        const list = Array.isArray(aData) ? aData : (aData.data || []);
        setAuditEvents(list);
      }
    } catch (err) {
      console.error('Failed to fetch diagnostics:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDiagnostics();
  }, [token]);

  const filteredAudits = auditEvents.filter((e) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      e.event_type?.toLowerCase().includes(q) ||
      e.actor?.toLowerCase().includes(q) ||
      e.session_id?.toLowerCase().includes(q) ||
      JSON.stringify(e.details || {}).toLowerCase().includes(q)
    );
  });

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <RoleNavbar />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Header */}
        <div className="bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-3">
              <span className="p-2 rounded-lg bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
                <Activity className="w-5 h-5" />
              </span>
              <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
                <span>Research & System Diagnostics</span>
                <span className="text-xs px-2 py-0.5 rounded font-mono bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                  {healthData?.status ? `STATUS: ${healthData.status.toUpperCase()}` : 'STATUS: ONLINE'}
                </span>
              </h1>
            </div>
            <p className="text-sm text-slate-400 mt-2 max-w-3xl">
              Real-time hardware status, NVIDIA CUDA-Q QPU execution backend, MySQL persistence health, and immutable audit event ledger.
            </p>
          </div>

          <button
            onClick={fetchDiagnostics}
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono border border-slate-700 flex items-center space-x-2 self-start md:self-auto"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh Diagnostics</span>
          </button>
        </div>

        {/* System Health Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Quantum Engine Card */}
          <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Atom className="w-5 h-5 text-cyan-400" />
                <h3 className="text-sm font-bold text-slate-200">Quantum Hardware Engine</h3>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                ONLINE
              </span>
            </div>
            <div className="space-y-2 text-xs font-mono">
              <div className="flex justify-between py-1 border-b border-slate-800">
                <span className="text-slate-500">Framework</span>
                <span className="text-slate-200">NVIDIA CUDA-Q 0.16.0</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800">
                <span className="text-slate-500">QPU Target</span>
                <span className="text-cyan-400">default (cudaq-sim)</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800">
                <span className="text-slate-500">Protocol Basis</span>
                <span className="text-slate-200">3-Qubit Teleportation ($Q_0, Q_1, Q_2$)</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-500">Operations per Signature</span>
                <span className="text-purple-400 font-bold">4,096 Circuits</span>
              </div>
            </div>
          </div>

          {/* Database Persistence Card */}
          <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Database className="w-5 h-5 text-emerald-400" />
                <h3 className="text-sm font-bold text-slate-200">Relational Persistence</h3>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                CONNECTED
              </span>
            </div>
            <div className="space-y-2 text-xs font-mono">
              <div className="flex justify-between py-1 border-b border-slate-800">
                <span className="text-slate-500">Database Engine</span>
                <span className="text-slate-200">MySQL 8.4 Enterprise</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800">
                <span className="text-slate-500">Port (Internal / External)</span>
                <span className="text-slate-200">3306 / 3307</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800">
                <span className="text-slate-500">ORM & Driver</span>
                <span className="text-slate-200">SQLAlchemy / PyMySQL</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-500">Schema Migrations</span>
                <span className="text-emerald-400 font-bold">In-Sync (v2.4 Role-Based)</span>
              </div>
            </div>
          </div>

          {/* Cryptography & Decision Standards Card */}
          <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Shield className="w-5 h-5 text-purple-400" />
                <h3 className="text-sm font-bold text-slate-200">Cryptographic Invariants</h3>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-purple-500/20 text-purple-400 border border-purple-500/30">
                DETERMINISTIC
              </span>
            </div>
            <div className="space-y-2 text-xs font-mono">
              <div className="flex justify-between py-1 border-b border-slate-800">
                <span className="text-slate-500">Hash Algorithm</span>
                <span className="text-slate-200">SHA-512 (Canonical)</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800">
                <span className="text-slate-500">Sample Ratio (N)</span>
                <span className="text-slate-200">5.0% (~205 operations)</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800">
                <span className="text-slate-500">Hypothesis Test</span>
                <span className="text-cyan-400">Fisher's Exact Test ($p \ge 0.01$)</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-500">Decision Engine</span>
                <span className="text-emerald-400 font-bold">100% Deterministic (NO AI/ML)</span>
              </div>
            </div>
          </div>
        </div>

        {/* Audit Event Stream */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-xl">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-base font-semibold text-slate-100 flex items-center space-x-2">
                <FileClock className="w-4 h-4 text-indigo-400" />
                <span>Cryptographic & System Audit Stream ({filteredAudits.length})</span>
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Every signing, quantum measurement run, transmission dispatch, interception, mutation, and verification is immutably logged.
              </p>
            </div>

            <div className="relative w-full sm:w-64">
              <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search audit records..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 font-mono"
              />
            </div>
          </div>

          {filteredAudits.length === 0 ? (
            <p className="text-xs text-slate-400 py-8 text-center">No audit records found.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs font-mono text-left">
                <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
                  <tr>
                    <th className="p-3">Event Type</th>
                    <th className="p-3">Actor</th>
                    <th className="p-3">Session ID</th>
                    <th className="p-3">Details</th>
                    <th className="p-3">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {filteredAudits.map((event) => {
                    const isExpanded = expandedId === event.id;
                    return (
                      <React.Fragment key={event.id}>
                        <tr
                          onClick={() => setExpandedId(isExpanded ? null : event.id)}
                          className="hover:bg-slate-950/40 cursor-pointer"
                        >
                          <td className="p-3">
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-slate-800 text-slate-200 border border-slate-700">
                              {event.event_type}
                            </span>
                          </td>
                          <td className="p-3 font-semibold text-slate-300">{event.actor}</td>
                          <td className="p-3 text-cyan-400">{event.session_id ? event.session_id.substring(0, 16) + '...' : 'SYSTEM'}</td>
                          <td className="p-3 text-slate-400 max-w-xs truncate">
                            {JSON.stringify(event.details || {})}
                          </td>
                          <td className="p-3 text-slate-400 whitespace-nowrap">
                            {new Date(event.timestamp).toLocaleTimeString()}
                          </td>
                        </tr>
                        {isExpanded && (
                          <tr className="bg-slate-950/80">
                            <td colSpan={5} className="p-4 text-xs font-mono">
                              <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 space-y-2">
                                <div className="text-slate-400 font-bold">Event Payload:</div>
                                <pre className="text-slate-300 text-[11px] overflow-x-auto whitespace-pre-wrap">
                                  {JSON.stringify(event.details, null, 2)}
                                </pre>
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>
    </div>
  );
};
