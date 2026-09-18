import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  CheckCircle2,
  RefreshCw,
  AlertTriangle,
  HelpCircle,
  Hash,
  Activity,
  History,
} from 'lucide-react';
import { api } from '../services/api';
import { VerificationResult, VerificationSample } from '../types';

interface VerificationPageProps {
  sessionId: string | null;
}

export const VerificationPage: React.FC<VerificationPageProps> = ({ sessionId }) => {
  const [results, setResults] = useState<VerificationResult[]>([]);
  const [samples, setSamples] = useState<VerificationSample[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedResultId, setSelectedResultId] = useState<string | null>(null);

  const fetchResults = async () => {
    if (!sessionId) return;
    setLoading(true);
    try {
      const [resData, sampleData] = await Promise.all([
        api.getVerificationResults(sessionId),
        api.getVerificationSamples(sessionId),
      ]);
      setResults(resData);
      setSamples(sampleData);
      if (resData.length > 0 && !selectedResultId) {
        setSelectedResultId(resData[resData.length - 1].id);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchResults();
  }, [sessionId]);

  if (!sessionId) {
    return (
      <div className="p-8 text-center bg-zaslon-900/60 border border-zaslon-border rounded-xl">
        <h2 className="text-sm font-semibold text-slate-300">No Session Selected</h2>
        <p className="text-xs text-slate-500 mt-1">Please select an active session to inspect verification decisions.</p>
      </div>
    );
  }

  // Active result to display
  const activeResult =
    results.find((r) => r.id === selectedResultId) ||
    (results.length > 0 ? results[results.length - 1] : null);

  const activeSample =
    activeResult && samples.find((s) => s.id === activeResult.sample_id)
      ? samples.find((s) => s.id === activeResult.sample_id)
      : samples.length > 0
      ? samples[samples.length - 1]
      : null;

  // Safe odds ratio formatter preventing null .toFixed crashes
  const formatOddsRatio = (val: number | null | undefined, display?: string): string => {
    if (display) return display;
    if (val === null || val === undefined) return 'Infinity';
    if (!isFinite(val)) return 'Infinity';
    return val.toFixed(4);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-100">Verification & Statistical Analysis</h1>
          <p className="text-xs text-slate-400 mt-1">
            Explainable verification decisions derived from 5% sample mismatch analysis and Fisher's Exact Test.
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={fetchResults}
            className="px-3 py-1.5 rounded-lg border border-zaslon-border bg-zaslon-850 hover:bg-zaslon-800 text-xs text-slate-300 flex items-center space-x-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {activeResult ? (
        <div className="space-y-6">
          {/* Top Decision Banner Card */}
          <div
            className={`p-6 rounded-xl border transition-all ${
              activeResult.security_decision === 'VERIFIED'
                ? 'bg-emerald-950/20 border-emerald-500/40 shadow-[0_0_20px_rgba(16,185,129,0.08)]'
                : 'bg-rose-950/20 border-rose-500/40 shadow-[0_0_20px_rgba(244,63,94,0.08)]'
            }`}
          >
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="flex items-center space-x-3.5">
                {activeResult.security_decision === 'VERIFIED' ? (
                  <div className="w-12 h-12 rounded-xl bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400">
                    <CheckCircle2 className="w-7 h-7" />
                  </div>
                ) : (
                  <div className="w-12 h-12 rounded-xl bg-rose-500/20 border border-rose-500/40 flex items-center justify-center text-rose-400">
                    <ShieldAlert className="w-7 h-7" />
                  </div>
                )}
                <div>
                  <div className="text-xs font-mono uppercase tracking-wider text-slate-400">
                    Multi-Signal Cybersecurity Decision
                  </div>
                  <h2
                    className={`text-2xl font-bold font-mono tracking-wide mt-0.5 ${
                      activeResult.security_decision === 'VERIFIED' ? 'text-emerald-400' : 'text-rose-400'
                    }`}
                  >
                    {activeResult.security_decision}
                  </h2>
                </div>
              </div>

              <div className="text-right font-mono text-xs">
                <div className="text-slate-400">
                  Evaluated: {new Date(activeResult.verified_at).toLocaleTimeString()}
                </div>
                {activeResult.attack_detected ? (
                  <div className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded bg-rose-500/20 border border-rose-500/40 text-rose-400 font-bold mt-1.5">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    <span>THREAT DETECTED: {activeResult.attack_category || 'INTERCEPTED'}</span>
                  </div>
                ) : (
                  <div className="text-emerald-400 font-semibold mt-1">NO THREAT DETECTED</div>
                )}
              </div>
            </div>

            <div className="mt-4 p-3.5 rounded-lg bg-zaslon-900/90 border border-zaslon-border text-xs text-slate-200 space-y-1">
              <div className="font-semibold text-slate-400 font-mono text-[11px] uppercase tracking-wider flex items-center space-x-1.5">
                <HelpCircle className="w-3.5 h-3.5 text-zaslon-quantum" />
                <span>Deterministic Mathematical Rationale</span>
              </div>
              <p className="font-mono text-[12px] leading-relaxed text-slate-200">
                {activeResult.decision_reason}
              </p>
            </div>
          </div>

          {/* Quantitative Metrics Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl bg-zaslon-900/60 border border-zaslon-border">
              <div className="text-xs font-mono text-slate-400">Verification Sample Size</div>
              <div className="text-2xl font-bold font-mono text-slate-100 mt-1">
                {activeResult.sample_size}
              </div>
              <div className="text-[11px] text-slate-500 mt-1">5% of 4,096 Operations (~205)</div>
            </div>

            <div className="p-4 rounded-xl bg-zaslon-900/60 border border-zaslon-border">
              <div className="text-xs font-mono text-slate-400">Matches vs Mismatches</div>
              <div className="text-2xl font-bold font-mono text-slate-100 mt-1">
                <span className="text-emerald-400">{activeResult.match_count}</span>
                <span className="text-slate-500 mx-1">/</span>
                <span className={activeResult.mismatch_count > 0 ? 'text-rose-400' : 'text-slate-400'}>
                  {activeResult.mismatch_count}
                </span>
              </div>
              <div className="text-[11px] text-slate-500 mt-1">
                Mismatch Ratio: {(activeResult.mismatch_ratio * 100).toFixed(2)}% (Max: 2.50%)
              </div>
            </div>

            <div className="p-4 rounded-xl bg-zaslon-900/60 border border-zaslon-border">
              <div className="text-xs font-mono text-slate-400">Fisher Exact Test (p-value)</div>
              <div
                className={`text-2xl font-bold font-mono mt-1 ${
                  activeResult.fisher_p_value >= 0.01 ? 'text-emerald-400' : 'text-rose-400'
                }`}
              >
                {activeResult.fisher_p_value.toExponential(4)}
              </div>
              <div className="text-[11px] text-slate-500 mt-1">
                Significance: {activeResult.fisher_p_value >= 0.01 ? 'p >= α (0.01)' : 'p < α (0.01) [FORGERY]'}
              </div>
            </div>

            <div className="p-4 rounded-xl bg-zaslon-900/60 border border-zaslon-border">
              <div className="text-xs font-mono text-slate-400">Statistical Verdict</div>
              <div
                className={`text-2xl font-bold font-mono mt-1 ${
                  activeResult.statistical_verdict === 'ACCEPTABLE' ? 'text-emerald-400' : 'text-rose-400'
                }`}
              >
                {activeResult.statistical_verdict}
              </div>
              <div className="text-[11px] text-slate-500 mt-1">
                Odds Ratio: {formatOddsRatio(activeResult.fisher_odds_ratio, activeResult.odds_ratio_display)}
              </div>
            </div>
          </div>

          {/* Sample Metadata & Reproducibility Provenance */}
          {activeSample && (
            <div className="p-5 rounded-xl bg-zaslon-900/60 border border-zaslon-border space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Hash className="w-4 h-4 text-zaslon-quantum" />
                  <h3 className="text-xs font-mono uppercase tracking-wider text-slate-300 font-semibold">
                    Sample Provenance & Reproducibility Seed
                  </h3>
                </div>
                <span className="text-[11px] font-mono text-slate-500">
                  Ratio: {(activeSample.sample_ratio * 100).toFixed(1)}% &bull; Size: {activeSample.sample_size}
                </span>
              </div>

              <div className="text-xs font-mono text-slate-300">
                Deterministic Seed: <span className="text-sky-400 font-bold">{activeSample.sample_seed}</span>
              </div>

              <div className="p-3 rounded-lg bg-zaslon-850/60 border border-zaslon-border text-[11px] font-mono text-slate-400 break-all max-h-24 overflow-y-auto">
                <span className="text-slate-500">Sampled Indices [{activeSample.sampled_indices.length} total]: </span>
                {activeSample.sampled_indices.slice(0, 40).join(', ')} ... +
                {activeSample.sampled_indices.length - 40} more operations.
              </div>
            </div>
          )}

          {/* Verification History Table (if multiple runs exist) */}
          {results.length > 1 && (
            <div className="p-5 rounded-xl bg-zaslon-900/60 border border-zaslon-border space-y-3">
              <div className="flex items-center space-x-2">
                <History className="w-4 h-4 text-zaslon-quantum" />
                <h3 className="text-xs font-mono uppercase tracking-wider text-slate-300 font-semibold">
                  Session Verification History ({results.length} Evaluations)
                </h3>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs font-mono">
                  <thead>
                    <tr className="border-b border-zaslon-border text-slate-400">
                      <th className="pb-2">Timestamp</th>
                      <th className="pb-2">Decision</th>
                      <th className="pb-2">Mismatch Ratio</th>
                      <th className="pb-2">Fisher p-value</th>
                      <th className="pb-2">Threat Flag</th>
                      <th className="pb-2 text-right">Inspect</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zaslon-border/40">
                    {results.map((r) => (
                      <tr
                        key={r.id}
                        className={`hover:bg-zaslon-850/50 ${
                          selectedResultId === r.id ? 'bg-zaslon-800/40 text-slate-200' : 'text-slate-400'
                        }`}
                      >
                        <td className="py-2.5">{new Date(r.verified_at).toLocaleTimeString()}</td>
                        <td className="py-2.5">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              r.security_decision === 'VERIFIED'
                                ? 'bg-emerald-500/20 text-emerald-400'
                                : 'bg-rose-500/20 text-rose-400'
                            }`}
                          >
                            {r.security_decision}
                          </span>
                        </td>
                        <td className="py-2.5">{(r.mismatch_ratio * 100).toFixed(2)}%</td>
                        <td className="py-2.5">{r.fisher_p_value.toExponential(3)}</td>
                        <td className="py-2.5">
                          {r.attack_detected ? (
                            <span className="text-rose-400 font-semibold">{r.attack_category}</span>
                          ) : (
                            <span className="text-slate-500">None</span>
                          )}
                        </td>
                        <td className="py-2.5 text-right">
                          <button
                            onClick={() => setSelectedResultId(r.id)}
                            className="text-xs text-zaslon-quantum hover:underline"
                          >
                            View
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="p-8 text-center bg-zaslon-900/60 border border-zaslon-border rounded-xl">
          <Activity className="w-8 h-8 text-slate-600 mx-auto mb-2" />
          <p className="text-xs text-slate-400 font-medium">
            No verification result recorded for this session yet.
          </p>
          <p className="text-[11px] text-slate-500 mt-1">
            Execute verification in the QDS Pipeline or simulate a threat to generate evaluation reports.
          </p>
        </div>
      )}
    </div>
  );
};
