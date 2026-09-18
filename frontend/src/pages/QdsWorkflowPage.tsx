import React, { useState, useEffect } from 'react';
import { ShieldCheck, Lock, Radio, FileCheck, ArrowRight, RefreshCw } from 'lucide-react';
import { api } from '../services/api';
import { WorkflowOverview } from '../types';
import { useQuantumStatus } from '../hooks/useQuantumStatus';

interface QdsWorkflowPageProps {
  sessionId: string | null;
  onNavigate: (tab: any) => void;
}

export const QdsWorkflowPage: React.FC<QdsWorkflowPageProps> = ({ sessionId, onNavigate }) => {
  const [overview, setOverview] = useState<WorkflowOverview | null>(null);
  const [rawMessage, setRawMessage] = useState('SIH 26141: Highly sensitive quantum signed payload data.');
  const [loading, setLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  const {
    status: quantumStatus,
    isExecuting: isQuantumExecuting,
    progressPercentage,
    completedOperations,
    teleportationCount,
    currentBatch,
    totalBatches,
    startPolling,
    refresh: refreshQuantumStatus,
  } = useQuantumStatus(sessionId, {
    pollIntervalMs: 1200,
    onComplete: () => {
      fetchWorkflow();
      setStatusMsg('All 4,096 teleportation circuits successfully executed on CUDA-Q.');
    },
    onFail: (s) => {
      setStatusMsg(`Quantum Teleportation Error: ${s.error_message || 'Execution failed'}`);
    },
  });

  const fetchWorkflow = async () => {
    if (!sessionId) return;
    try {
      const data = await api.getWorkflowOverview(sessionId);
      setOverview(data);
    } catch (err: any) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchWorkflow();
  }, [sessionId]);

  const handleComputeHash = async () => {
    if (!sessionId) return;
    setLoading(true);
    setStatusMsg('Computing cryptographic SHA-512 digest...');
    try {
      await api.computeHash(sessionId, rawMessage, overview?.created_by || 'Alice_Signer');
      await fetchWorkflow();
      setStatusMsg('SHA-512 computed successfully.');
    } catch (err: any) {
      setStatusMsg(`Hash Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleLaunchTeleport = async () => {
    if (!sessionId) return;
    setLoading(true);
    setStatusMsg('Launching 4,096 3-qubit CUDA-Q teleportation operations in background...');
    try {
      await api.launchTeleportation(sessionId, overview?.created_by || 'Alice_Signer', 4096, 512, true);
      startPolling();
      await fetchWorkflow();
    } catch (err: any) {
      setStatusMsg(`Quantum Launch Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDeclare = async () => {
    if (!sessionId) return;
    setLoading(true);
    setStatusMsg('Publishing Public Declaration and cryptographic commitment...');
    try {
      await api.issueDeclaration(sessionId, overview?.created_by || 'Alice_Signer');
      await fetchWorkflow();
      setStatusMsg('Public declaration published and signature token active.');
    } catch (err: any) {
      setStatusMsg(`Declaration Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleVerify = async () => {
    if (!sessionId) return;
    setLoading(true);
    setStatusMsg('Extracting ~5% sample, evaluating Fisher Exact Test and security rules...');
    try {
      await api.verifySession(sessionId, overview?.verifier_id || 'Bob_Verifier', 0.05);
      await fetchWorkflow();
      setStatusMsg('Verification evaluation completed.');
      onNavigate('verification');
    } catch (err: any) {
      setStatusMsg(`Verification Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  if (!sessionId) {
    return (
      <div className="p-8 text-center bg-zaslon-900/60 border border-zaslon-border rounded-xl">
        <h2 className="text-sm font-semibold text-slate-300">No Session Selected</h2>
        <p className="text-xs text-slate-500 mt-1">Please select or create a session to view the pipeline.</p>
        <button
          onClick={() => onNavigate('sessions')}
          className="mt-4 px-4 py-2 rounded bg-zaslon-accent text-zaslon-950 text-xs font-semibold"
        >
          Go to Sessions
        </button>
      </div>
    );
  }

  const stages = overview?.stages;
  const isTeleported = stages?.quantum_stage.completed || quantumStatus?.status === 'COMPLETED';

  // 9 Architectural Pipeline Stages
  const pipelineStages = [
    { num: 1, name: 'Session Init', done: true },
    { num: 2, name: 'Plaintext', done: true },
    { num: 3, name: 'SHA-512', done: !!stages?.hash_stage.completed },
    { num: 4, name: 'State Prep', done: !!stages?.hash_stage.completed },
    { num: 5, name: '4,096 Teleportations', done: isTeleported },
    { num: 6, name: 'Declaration Token', done: !!stages?.declaration_stage.completed },
    { num: 7, name: '5% Sampling', done: !!stages?.verification_stage.completed },
    { num: 8, name: 'Fisher Test', done: !!stages?.verification_stage.completed },
    { num: 9, name: 'Decision Engine', done: !!stages?.verification_stage.completed },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-100">
            QDS End-to-End Pipeline
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Session: <span className="font-mono text-zaslon-quantum">{overview?.session_name}</span> &bull; Status:{' '}
            <span className="font-mono text-slate-200">{overview?.status}</span>
          </p>
        </div>

        <div className="flex items-center space-x-2">
          {statusMsg && (
            <div className="text-xs font-mono px-3 py-1.5 rounded bg-zaslon-850 border border-zaslon-border text-slate-300">
              {statusMsg}
            </div>
          )}
          <button
            onClick={() => {
              fetchWorkflow();
              refreshQuantumStatus();
            }}
            className="p-1.5 rounded border border-zaslon-border bg-zaslon-850 hover:bg-zaslon-800 text-slate-300"
            title="Refresh pipeline status"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* 9-Stage Visual Protocol Progress Tracker */}
      <div className="p-4 rounded-xl border border-zaslon-border bg-zaslon-900/60 overflow-x-auto">
        <div className="text-[11px] font-mono uppercase tracking-wider text-slate-400 font-semibold mb-3 flex items-center justify-between">
          <span>9-Stage Deterministic QDS Architecture</span>
          <span className="text-slate-500 font-normal lowercase">cudaq &bull; sha-512 &bull; fisher's exact test</span>
        </div>
        <div className="flex items-center min-w-[760px] justify-between relative">
          <div className="absolute top-3.5 left-4 right-4 h-0.5 bg-zaslon-800 -z-0" />
          {pipelineStages.map((st) => (
            <div key={st.num} className="flex flex-col items-center relative z-10 space-y-1">
              <div
                className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-mono font-bold transition-all ${
                  st.done
                    ? 'bg-zaslon-accent text-zaslon-950 ring-4 ring-zaslon-accent/20'
                    : 'bg-zaslon-850 border border-zaslon-border text-slate-500'
                }`}
              >
                {st.done ? '✓' : st.num}
              </div>
              <span
                className={`text-[10px] font-mono text-center whitespace-nowrap ${
                  st.done ? 'text-slate-200 font-medium' : 'text-slate-500'
                }`}
              >
                {st.name}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Step 1: Message Input & Hashing */}
      <div className="p-5 rounded-xl border border-zaslon-border bg-zaslon-900/60 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="w-6 h-6 rounded-full bg-zaslon-accent/20 border border-zaslon-accent/40 flex items-center justify-center text-zaslon-accent text-xs font-bold font-mono">
              1
            </div>
            <h3 className="text-xs font-mono uppercase tracking-wider text-slate-300 font-semibold">
              Plaintext Input & SHA-512 Cryptographic Hashing
            </h3>
          </div>
          {stages?.hash_stage.completed && (
            <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-[10px] font-mono">
              COMPLETED
            </span>
          )}
        </div>

        <textarea
          rows={2}
          value={rawMessage}
          onChange={(e) => setRawMessage(e.target.value)}
          placeholder="Enter message text to sign..."
          className="w-full px-3 py-2 rounded bg-zaslon-850 border border-zaslon-border text-xs text-slate-200 focus:outline-none focus:border-zaslon-accent font-mono"
        />

        {stages?.hash_stage.sha512_digest && (
          <div className="p-2.5 rounded bg-zaslon-850/60 border border-zaslon-border text-[11px] font-mono text-slate-400 break-all">
            <span className="text-slate-500">SHA-512 Digest: </span>
            <span className="text-sky-400 font-semibold">{stages.hash_stage.sha512_digest}</span>
          </div>
        )}

        <button
          onClick={handleComputeHash}
          disabled={loading || isQuantumExecuting}
          className="px-4 py-2 rounded bg-zaslon-800 hover:bg-zaslon-700 border border-zaslon-border text-xs font-medium text-slate-200 flex items-center space-x-2 disabled:opacity-50"
        >
          <Lock className="w-3.5 h-3.5 text-zaslon-quantum" />
          <span>Compute SHA-512</span>
        </button>
      </div>

      {/* Step 2: Teleportation */}
      <div className="p-5 rounded-xl border border-zaslon-border bg-zaslon-900/60 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="w-6 h-6 rounded-full bg-zaslon-accent/20 border border-zaslon-accent/40 flex items-center justify-center text-zaslon-accent text-xs font-bold font-mono">
              2
            </div>
            <h3 className="text-xs font-mono uppercase tracking-wider text-slate-300 font-semibold">
              3-Qubit Quantum Teleportation (CUDA-Q Engine)
            </h3>
          </div>
          {isTeleported && !isQuantumExecuting && (
            <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-[10px] font-mono">
              4,096 OPERATIONS EXECUTED
            </span>
          )}
        </div>

        <p className="text-xs text-slate-400">
          Deterministic PRF maps SHA-512 to 4,096 quantum state preparations (θ_k, φ_k). Teleportation circuits execute on NVIDIA CUDA-Q with Bell-pair entanglement and feed-forward corrections (X^(m₁) Z^(m₀)).
        </p>

        {/* Live Quantum Execution Progress Card */}
        {isQuantumExecuting && (
          <div className="p-4 rounded-lg bg-zaslon-850/80 border border-zaslon-quantum/40 space-y-2.5">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-zaslon-quantum font-semibold flex items-center space-x-1.5">
                <Radio className="w-4 h-4 animate-pulse" />
                <span>CUDA-Q Teleportation Running...</span>
              </span>
              <span className="text-slate-300 font-bold">{progressPercentage.toFixed(1)}%</span>
            </div>

            <div className="w-full bg-zaslon-950 rounded-full h-2 overflow-hidden border border-zaslon-border">
              <div
                className="bg-zaslon-quantum h-full transition-all duration-300 ease-out"
                style={{ width: `${Math.max(4, Math.min(100, progressPercentage))}%` }}
              />
            </div>

            <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
              <span>
                Operations: <span className="text-slate-200">{completedOperations}</span> / {teleportationCount}
              </span>
              <span>
                Batch: <span className="text-slate-200">{currentBatch}</span> / {totalBatches}
              </span>
            </div>
          </div>
        )}

        <div className="flex items-center space-x-3">
          <button
            onClick={handleLaunchTeleport}
            disabled={loading || isQuantumExecuting || !stages?.hash_stage.completed}
            className="px-4 py-2 rounded bg-zaslon-800 hover:bg-zaslon-700 border border-zaslon-border text-xs font-medium text-slate-200 flex items-center space-x-2 disabled:opacity-50"
          >
            <Radio className="w-3.5 h-3.5 text-zaslon-quantum" />
            <span>{isQuantumExecuting ? 'Executing Circuits...' : 'Launch 4,096 Teleportations'}</span>
          </button>
          <button
            onClick={() => onNavigate('teleportation')}
            className="text-xs text-zaslon-quantum hover:underline flex items-center space-x-1"
          >
            <span>View Measurements & Circuit Topology</span>
            <ArrowRight className="w-3.5 h-3.5 ml-0.5" />
          </button>
        </div>
      </div>

      {/* Step 3: Public Declaration */}
      <div className="p-5 rounded-xl border border-zaslon-border bg-zaslon-900/60 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="w-6 h-6 rounded-full bg-zaslon-accent/20 border border-zaslon-accent/40 flex items-center justify-center text-zaslon-accent text-xs font-bold font-mono">
              3
            </div>
            <h3 className="text-xs font-mono uppercase tracking-wider text-slate-300 font-semibold">
              Public Declaration & Single-Use Token Commitment
            </h3>
          </div>
          {stages?.declaration_stage.completed && (
            <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-[10px] font-mono">
              ACTIVE DECLARATION
            </span>
          )}
        </div>

        <p className="text-xs text-slate-400">
          Signer commits to the session ID, SHA-512 message digest, and quantum run ID via HMAC-SHA512. The generated signature token is strictly single-use to prevent replay attacks.
        </p>

        {stages?.declaration_stage.token && (
          <div className="p-2.5 rounded bg-zaslon-850/60 border border-zaslon-border text-[11px] font-mono text-slate-400 break-all space-y-1">
            <div>
              <span className="text-slate-500">Signature Token: </span>
              <span className="text-sky-400 font-semibold">{stages.declaration_stage.token}</span>
            </div>
            <div className="text-[10px] text-slate-500">
              State: <span className="text-emerald-400">Valid Single-Use Cryptographic Commitment</span>
            </div>
          </div>
        )}

        <button
          onClick={handleDeclare}
          disabled={loading || isQuantumExecuting || !isTeleported}
          className="px-4 py-2 rounded bg-zaslon-800 hover:bg-zaslon-700 border border-zaslon-border text-xs font-medium text-slate-200 flex items-center space-x-2 disabled:opacity-50"
        >
          <FileCheck className="w-3.5 h-3.5 text-zaslon-quantum" />
          <span>Publish Declaration</span>
        </button>
      </div>

      {/* Step 4: Verification */}
      <div className="p-5 rounded-xl border border-zaslon-border bg-zaslon-900/60 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="w-6 h-6 rounded-full bg-zaslon-accent/20 border border-zaslon-accent/40 flex items-center justify-center text-zaslon-accent text-xs font-bold font-mono">
              4
            </div>
            <h3 className="text-xs font-mono uppercase tracking-wider text-slate-300 font-semibold">
              Deterministic Sampling, Fisher's Exact Test & Cybersecurity Engine
            </h3>
          </div>
          {stages?.verification_stage.completed && (
            <span
              className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                stages.verification_stage.decision === 'VERIFIED'
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                  : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
              }`}
            >
              {stages.verification_stage.decision}
            </span>
          )}
        </div>

        <p className="text-xs text-slate-400">
          Verifier (Bob) deterministically selects ~5% of operations (N_sample ≈ 205), calculates empirical mismatch ratio, runs Fisher's Exact Test against the baseline noise rate (p ≥ α), and enforces all 5 security invariants.
        </p>

        <div className="flex items-center space-x-3">
          <button
            onClick={handleVerify}
            disabled={loading || isQuantumExecuting || !stages?.declaration_stage.completed}
            className="px-4 py-2 rounded bg-zaslon-accent hover:bg-sky-500 text-zaslon-950 text-xs font-semibold flex items-center space-x-2 disabled:opacity-50 shadow"
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Verify Signature ({overview?.verifier_id || 'Bob'})</span>
          </button>
          {stages?.verification_stage.completed && (
            <button
              onClick={() => onNavigate('verification')}
              className="text-xs text-zaslon-quantum hover:underline flex items-center space-x-1"
            >
              <span>Inspect Statistical Verification Report</span>
              <ArrowRight className="w-3.5 h-3.5 ml-0.5" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
