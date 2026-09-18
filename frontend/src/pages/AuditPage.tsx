import React, { useState, useEffect } from 'react';
import {
  RefreshCw,
  Filter,
  Search,
  FileClock,
  ShieldCheck,
  ShieldAlert,
  Radio,
  Lock,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { api } from '../services/api';
import { AuditEvent } from '../types';

interface AuditPageProps {
  sessionId: string | null;
}

export const AuditPage: React.FC<AuditPageProps> = ({ sessionId }) => {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [filterSessionOnly, setFilterSessionOnly] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('ALL');
  const [expandedEventId, setExpandedEventId] = useState<number | null>(null);

  const fetchAudit = async () => {
    setLoading(true);
    try {
      const data = await api.getAuditTrail(filterSessionOnly && sessionId ? sessionId : undefined, 150);
      setEvents(data);
    } catch (err) {
      console.error('Failed to load audit trail:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAudit();
  }, [sessionId, filterSessionOnly]);

  const filteredEvents = events.filter((e) => {
    // Category filter
    if (categoryFilter !== 'ALL') {
      if (!e.event_type.startsWith(categoryFilter)) return false;
    }
    // Search query
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchType = e.event_type.toLowerCase().includes(q);
      const matchActor = e.actor.toLowerCase().includes(q);
      const matchSess = e.session_id ? e.session_id.toLowerCase().includes(q) : false;
      const matchDetails = JSON.stringify(e.details).toLowerCase().includes(q);
      if (!matchType && !matchActor && !matchSess && !matchDetails) return false;
    }
    return true;
  });

  const getEventBadge = (type: string) => {
    if (type.includes('ATTACK') || type.includes('TAMPER') || type.includes('REJECTED')) {
      return (
        <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded bg-rose-500/20 text-rose-400 border border-rose-500/30 font-bold">
          <ShieldAlert className="w-3 h-3" />
          <span>{type}</span>
        </span>
      );
    }
    if (type.includes('VERIF') || type.includes('SUCCESS') || type.includes('COMPLETED')) {
      return (
        <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-medium">
          <ShieldCheck className="w-3 h-3" />
          <span>{type}</span>
        </span>
      );
    }
    if (type.includes('TELEPORT') || type.includes('QUANTUM')) {
      return (
        <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded bg-sky-500/20 text-sky-400 border border-sky-500/30 font-medium">
          <Radio className="w-3 h-3" />
          <span>{type}</span>
        </span>
      );
    }
    if (type.includes('HASH')) {
      return (
        <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30 font-medium">
          <Lock className="w-3 h-3" />
          <span>{type}</span>
        </span>
      );
    }
    return (
      <span className="px-2 py-0.5 rounded bg-zaslon-800 text-slate-300 border border-zaslon-border">
        {type}
      </span>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-100">Security Audit Trail</h1>
          <p className="text-xs text-slate-400 mt-1">
            Tamper-evident log tracking cryptographic hashing, teleportation batches, declarations, verifications, and intercepted attacks.
          </p>
        </div>
        <div className="flex items-center space-x-3">
          {sessionId && (
            <button
              onClick={() => setFilterSessionOnly(!filterSessionOnly)}
              className={`px-3 py-1.5 rounded-lg border text-xs font-mono flex items-center space-x-1.5 transition-colors ${
                filterSessionOnly
                  ? 'bg-zaslon-800 border-zaslon-accent text-zaslon-quantum'
                  : 'bg-zaslon-850 border-zaslon-border text-slate-400 hover:text-slate-200'
              }`}
            >
              <Filter className="w-3.5 h-3.5" />
              <span>Current Session Only</span>
            </button>
          )}
          <button
            onClick={fetchAudit}
            className="px-3 py-1.5 rounded-lg border border-zaslon-border bg-zaslon-850 hover:bg-zaslon-800 text-xs text-slate-300 flex items-center space-x-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="p-4 rounded-xl border border-zaslon-border bg-zaslon-900/60 flex flex-wrap items-center justify-between gap-3 text-xs font-mono">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-slate-500">Category:</span>
          {['ALL', 'SESSION', 'HASH', 'TELEPORT', 'DECLARATION', 'VERIF', 'ATTACK'].map((cat) => (
            <button
              key={cat}
              onClick={() => setCategoryFilter(cat)}
              className={`px-2.5 py-1 rounded transition-colors ${
                categoryFilter === cat
                  ? 'bg-zaslon-accent text-zaslon-950 font-bold'
                  : 'bg-zaslon-850 text-slate-400 hover:text-slate-200 border border-zaslon-border'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        <div className="relative flex items-center">
          <Search className="w-3.5 h-3.5 absolute left-2.5 text-slate-500" />
          <input
            type="text"
            placeholder="Search audit trail..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-8 pr-3 py-1.5 rounded-lg bg-zaslon-850 border border-zaslon-border text-xs text-slate-200 w-56 focus:outline-none focus:border-zaslon-accent"
          />
        </div>
      </div>

      {/* Audit Table */}
      <div className="rounded-xl border border-zaslon-border bg-zaslon-900/60 overflow-hidden">
        <div className="p-3 border-b border-zaslon-border flex items-center justify-between text-xs font-mono text-slate-400 bg-zaslon-850/30">
          <span>
            Displaying <span className="text-slate-200 font-bold">{filteredEvents.length}</span> recorded audit events
          </span>
          <span className="text-[11px] text-slate-500">Cryptographically verifiable sequence</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-zaslon-border bg-zaslon-850/40 text-slate-400">
                <th className="p-3.5 font-medium">Timestamp</th>
                <th className="p-3.5 font-medium">Event Type</th>
                <th className="p-3.5 font-medium">Actor</th>
                <th className="p-3.5 font-medium">Session ID</th>
                <th className="p-3.5 font-medium">Details Payload</th>
                <th className="p-3.5 font-medium text-right">Inspect</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zaslon-border/40">
              {filteredEvents.map((e) => {
                const isExpanded = expandedEventId === e.id;
                return (
                  <React.Fragment key={e.id}>
                    <tr
                      onClick={() => setExpandedEventId(isExpanded ? null : e.id)}
                      className={`hover:bg-zaslon-850/50 cursor-pointer transition-colors ${
                        isExpanded ? 'bg-zaslon-800/40' : ''
                      }`}
                    >
                      <td className="p-3.5 text-slate-400 whitespace-nowrap">
                        {new Date(e.timestamp).toLocaleString()}
                      </td>
                      <td className="p-3.5">{getEventBadge(e.event_type)}</td>
                      <td className="p-3.5 text-sky-400 font-semibold">{e.actor}</td>
                      <td className="p-3.5 text-slate-500">
                        {e.session_id ? `${e.session_id.substring(0, 8)}...` : 'GLOBAL'}
                      </td>
                      <td className="p-3.5 text-slate-400 text-[11px] max-w-sm truncate">
                        {JSON.stringify(e.details)}
                      </td>
                      <td className="p-3.5 text-right">
                        <button
                          onClick={(evt) => {
                            evt.stopPropagation();
                            setExpandedEventId(isExpanded ? null : e.id);
                          }}
                          className="p-1 rounded text-slate-400 hover:text-slate-200"
                        >
                          {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                        </button>
                      </td>
                    </tr>

                    {/* Expandable JSON details row */}
                    {isExpanded && (
                      <tr className="bg-zaslon-950/80">
                        <td colSpan={6} className="p-4 border-y border-zaslon-border/60">
                          <div className="space-y-2">
                            <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono">
                              <span className="font-semibold text-slate-300">
                                Full Event Payload (Audit ID #{e.id})
                              </span>
                              <span>Session: {e.session_id || 'N/A'}</span>
                            </div>
                            <pre className="p-3 rounded-lg bg-zaslon-900 border border-zaslon-border text-[11px] font-mono text-sky-300 overflow-x-auto whitespace-pre-wrap break-all">
                              {JSON.stringify(e.details, null, 2)}
                            </pre>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}

              {filteredEvents.length === 0 && !loading && (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-slate-500 font-sans">
                    <FileClock className="w-8 h-8 mx-auto mb-2 text-slate-600" />
                    No audit records match the selected filter.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
