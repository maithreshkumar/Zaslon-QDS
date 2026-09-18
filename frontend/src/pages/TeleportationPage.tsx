import React, { useState, useEffect } from 'react';
import { RefreshCw, ChevronLeft, ChevronRight, Eye, Radio, CheckCircle2, XCircle, Search } from 'lucide-react';
import { api } from '../services/api';
import { Measurement } from '../types';
import { CircuitDiagram } from '../components/circuit/CircuitDiagram';
import { useQuantumStatus } from '../hooks/useQuantumStatus';

interface TeleportationPageProps {
  sessionId: string | null;
}

export const TeleportationPage: React.FC<TeleportationPageProps> = ({ sessionId }) => {
  const [measurements, setMeasurements] = useState<Measurement[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [loading, setLoading] = useState(false);
  const [selectedOp, setSelectedOp] = useState<Measurement | null>(null);
  const [searchIndex, setSearchIndex] = useState('');

  const {
    isExecuting: isQuantumExecuting,
    progressPercentage,
    completedOperations,
    currentBatch,
    totalBatches,
    refresh: refreshQuantumStatus,
  } = useQuantumStatus(sessionId, {
    pollIntervalMs: 1500,
    onComplete: () => {
      fetchMeasurements(1);
    },
  });

  const fetchMeasurements = async (p = 1, size = pageSize) => {
    if (!sessionId) return;
    setLoading(true);
    try {
      const res = await api.getMeasurements(sessionId, p, size);
      setMeasurements(res.items);
      setTotal(res.total);
      setPage(res.page);
      if (res.items.length > 0 && !selectedOp) {
        setSelectedOp(res.items[0]);
      } else if (res.items.length > 0 && selectedOp) {
        const match = res.items.find((m) => m.id === selectedOp.id);
        if (match) setSelectedOp(match);
      }
    } catch (err) {
      console.error('Failed to load measurements:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMeasurements(1);
  }, [sessionId, pageSize]);

  if (!sessionId) {
    return (
      <div className="p-8 text-center bg-zaslon-900/60 border border-zaslon-border rounded-xl">
        <h2 className="text-sm font-semibold text-slate-300">No Session Selected</h2>
        <p className="text-xs text-slate-500 mt-1">Please select an active session to inspect quantum teleportations.</p>
      </div>
    );
  }

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  // Compute stats from current loaded measurements (or total if available)
  const currentMatches = measurements.filter((m) => m.is_match).length;
  const currentMismatches = measurements.length - currentMatches;
  const currentMatchRate = measurements.length > 0 ? (currentMatches / measurements.length) * 100 : 100;

  const handleSearchJump = (e: React.FormEvent) => {
    e.preventDefault();
    const idx = parseInt(searchIndex, 10);
    if (!isNaN(idx) && idx >= 0 && idx < total) {
      const targetPage = Math.floor(idx / pageSize) + 1;
      fetchMeasurements(targetPage).then(() => {
        const found = measurements.find((m) => m.operation_index === idx);
        if (found) setSelectedOp(found);
      });
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-100">Quantum Teleportation Workload</h1>
          <p className="text-xs text-slate-400 mt-1">
            Real 3-qubit Bell-state teleportation circuits executed on NVIDIA CUDA-Q ({total.toLocaleString()} operations).
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <form onSubmit={handleSearchJump} className="relative flex items-center">
            <Search className="w-3.5 h-3.5 absolute left-2.5 text-slate-500" />
            <input
              type="number"
              min={0}
              max={Math.max(0, total - 1)}
              placeholder="Jump to Op #..."
              value={searchIndex}
              onChange={(e) => setSearchIndex(e.target.value)}
              className="pl-8 pr-3 py-1.5 rounded-lg bg-zaslon-850 border border-zaslon-border text-xs font-mono text-slate-200 w-36 focus:outline-none focus:border-zaslon-accent"
            />
          </form>
          <button
            onClick={() => {
              fetchMeasurements(page);
              refreshQuantumStatus();
            }}
            className="px-3 py-1.5 rounded-lg border border-zaslon-border bg-zaslon-850 hover:bg-zaslon-800 text-xs text-slate-300 flex items-center space-x-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Summary Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-zaslon-900/60 border border-zaslon-border">
          <div className="text-xs font-mono uppercase text-slate-400">Total Teleportations</div>
          <div className="text-2xl font-bold font-mono text-slate-100 mt-1">{total.toLocaleString()}</div>
          <div className="text-[11px] text-slate-500 mt-1">Target: 4,096 Operations</div>
        </div>

        <div className="p-4 rounded-xl bg-zaslon-900/60 border border-zaslon-border">
          <div className="text-xs font-mono uppercase text-slate-400">Sample Fidelity</div>
          <div className="text-2xl font-bold font-mono text-emerald-400 mt-1">
            {currentMatchRate.toFixed(2)}%
          </div>
          <div className="text-[11px] text-slate-500 mt-1">Empirical Match Rate</div>
        </div>

        <div className="p-4 rounded-xl bg-zaslon-900/60 border border-zaslon-border">
          <div className="text-xs font-mono uppercase text-slate-400">Matches (Current View)</div>
          <div className="text-2xl font-bold font-mono text-emerald-400 mt-1 flex items-center space-x-2">
            <span>{currentMatches}</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400/80" />
          </div>
          <div className="text-[11px] text-slate-500 mt-1">Matching expected bit</div>
        </div>

        <div className="p-4 rounded-xl bg-zaslon-900/60 border border-zaslon-border">
          <div className="text-xs font-mono uppercase text-slate-400">Mismatches (Current View)</div>
          <div
            className={`text-2xl font-bold font-mono mt-1 flex items-center space-x-2 ${
              currentMismatches > 0 ? 'text-rose-400' : 'text-slate-400'
            }`}
          >
            <span>{currentMismatches}</span>
            {currentMismatches > 0 && <XCircle className="w-4 h-4 text-rose-400/80" />}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">Permissible baseline: &lt; 2.5%</div>
        </div>
      </div>

      {/* Live Quantum Execution Card */}
      {isQuantumExecuting && (
        <div className="p-5 rounded-xl bg-zaslon-900/80 border border-zaslon-quantum/50 shadow-md space-y-3">
          <div className="flex items-center justify-between text-xs font-mono">
            <span className="text-zaslon-quantum font-semibold flex items-center space-x-2">
              <Radio className="w-4 h-4 animate-pulse text-zaslon-quantum" />
              <span>CUDA-Q Teleportation Pipeline Running in Background</span>
            </span>
            <span className="text-slate-200 font-bold">{progressPercentage.toFixed(1)}%</span>
          </div>

          <div className="w-full bg-zaslon-950 rounded-full h-2.5 overflow-hidden border border-zaslon-border">
            <div
              className="bg-zaslon-quantum h-full transition-all duration-300"
              style={{ width: `${Math.max(4, Math.min(100, progressPercentage))}%` }}
            />
          </div>

          <div className="flex items-center justify-between text-xs font-mono text-slate-400">
            <span>
              Completed Operations: <span className="text-slate-200">{completedOperations}</span> / 4,096
            </span>
            <span>
              Batch Progress: <span className="text-slate-200">{currentBatch}</span> / {totalBatches}
            </span>
          </div>
        </div>
      )}

      {/* Circuit Diagram for inspected operation */}
      {selectedOp && (
        <CircuitDiagram
          operationIndex={selectedOp.operation_index}
          theta={selectedOp.prep_theta}
          phi={selectedOp.prep_phi}
          basis={selectedOp.prep_phi !== 0 || Math.abs(selectedOp.prep_theta - Math.PI / 2) < 0.01 ? 'X' : 'Z'}
          m0={selectedOp.alice_m0}
          m1={selectedOp.alice_m1}
          bobObserved={selectedOp.bob_observed_bit}
          expectedBit={selectedOp.expected_bit}
        />
      )}

      {/* Measurement Table */}
      <div className="rounded-xl border border-zaslon-border bg-zaslon-900/60 overflow-hidden">
        <div className="p-3 border-b border-zaslon-border flex flex-wrap items-center justify-between gap-2 text-xs font-mono text-slate-400 bg-zaslon-850/30">
          <span>
            Showing operations {total === 0 ? 0 : (page - 1) * pageSize + 1} to{' '}
            {Math.min(page * pageSize, total)} of {total.toLocaleString()}
          </span>

          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-1.5 text-xs">
              <span className="text-slate-500">Per page:</span>
              <select
                value={pageSize}
                onChange={(e) => setPageSize(Number(e.target.value))}
                className="bg-zaslon-850 border border-zaslon-border rounded px-2 py-0.5 text-slate-200 focus:outline-none"
              >
                <option value={25}>25</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
              </select>
            </div>

            <div className="flex items-center space-x-2">
              <button
                disabled={page <= 1}
                onClick={() => fetchMeasurements(page - 1)}
                className="p-1 rounded border border-zaslon-border disabled:opacity-30 hover:bg-zaslon-800"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span>
                Page {page} of {totalPages}
              </span>
              <button
                disabled={page >= totalPages}
                onClick={() => fetchMeasurements(page + 1)}
                className="p-1 rounded border border-zaslon-border disabled:opacity-30 hover:bg-zaslon-800"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-zaslon-border bg-zaslon-850/40 text-slate-400">
                <th className="p-3 font-medium">Index</th>
                <th className="p-3 font-medium">Prep (θ, φ)</th>
                <th className="p-3 font-medium">Expected</th>
                <th className="p-3 font-medium">Alice (M₀, M₁)</th>
                <th className="p-3 font-medium">Bob Corr (X, Z)</th>
                <th className="p-3 font-medium">Bob Observed</th>
                <th className="p-3 font-medium">Fidelity Match</th>
                <th className="p-3 font-medium text-right">Inspect Circuit</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zaslon-border/40">
              {measurements.map((m) => {
                const isSelected = selectedOp?.id === m.id;
                return (
                  <tr
                    key={m.id}
                    onClick={() => setSelectedOp(m)}
                    className={`hover:bg-zaslon-850/50 transition-colors cursor-pointer ${
                      isSelected ? 'bg-zaslon-800/50 ring-1 ring-zaslon-accent/30' : ''
                    }`}
                  >
                    <td className="p-3 font-semibold text-slate-300">#{m.operation_index}</td>
                    <td className="p-3 text-slate-400">
                      ({m.prep_theta.toFixed(2)}, {m.prep_phi.toFixed(2)})
                    </td>
                    <td className="p-3 font-bold text-sky-400">{m.expected_bit}</td>
                    <td className="p-3 text-slate-300">
                      ({m.alice_m0}, {m.alice_m1})
                    </td>
                    <td className="p-3 text-slate-400">
                      X={m.bob_correction_x}, Z={m.bob_correction_z}
                    </td>
                    <td className="p-3 font-bold text-slate-200">{m.bob_observed_bit}</td>
                    <td className="p-3">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          m.is_match
                            ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                            : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                        }`}
                      >
                        {m.is_match ? 'MATCH' : 'MISMATCH'}
                      </span>
                    </td>
                    <td className="p-3 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedOp(m);
                        }}
                        className={`p-1.5 rounded transition-colors ${
                          isSelected
                            ? 'text-zaslon-quantum bg-zaslon-800 border border-zaslon-border'
                            : 'text-slate-400 hover:text-slate-200'
                        }`}
                        title="View Quantum Circuit"
                      >
                        <Eye className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                );
              })}
              {measurements.length === 0 && !loading && (
                <tr>
                  <td colSpan={8} className="p-8 text-center text-slate-500 font-sans">
                    No quantum measurements recorded for this session yet. Launch teleportation in the pipeline to generate real 3-qubit circuits.
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
