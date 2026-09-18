import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  Bug,
  RefreshCw,
  Zap,
  ArrowRight,
  Lock,
  UserX,
  Repeat,
  FileWarning,
} from 'lucide-react';
import { api } from '../services/api';
import { AttackEvent, VerificationResult } from '../types';
import { useSession } from '../context/SessionContext';

interface AttackSimulationPageProps {
  sessionId: string | null;
  onNavigate?: (tab: any) => void;
}

export const AttackSimulationPage: React.FC<AttackSimulationPageProps> = ({
  sessionId,
  onNavigate,
}) => {
  const { currentSession } = useSession();
  const [events, setEvents] = useState<AttackEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [lastInterception, setLastInterception] = useState<VerificationResult | null>(null);

  const fetchAttacks = async () => {
    if (!sessionId) return;
    setLoading(true);
    try {
      const data = await api.getAttackEvents(sessionId);
      setEvents(data);
    } catch (err) {
      console.error('Failed to fetch attack events:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAttacks();
  }, [sessionId]);

  const runAttack = async (type: string, autoDetect = false) => {
    if (!sessionId) return;
    setLoading(true);
    setLastInterception(null);
    setFeedback(`Injecting controlled ${type} cyber threat into active session state...`);

    try {
      // 1. Simulate the genuine database mutation
      const event = await api.simulateAttack(sessionId, type);
      setEvents((prev) => [event, ...prev]);

      if (autoDetect) {
        setFeedback(`Threat injected. Passing through authentic cybersecurity verification pipeline...`);
        // If Unauthorized Verification, test with an unauthorized actor 'Mallory_Attacker'
        const verifierToUse =
          type === 'UNAUTHORIZED_VERIFICATION'
            ? 'Mallory_Attacker'
            : currentSession?.verifier_id || 'Bob_Verifier';

        const verifResult = await api.verifySession(sessionId, verifierToUse, 0.05);
        setLastInterception(verifResult);
        setFeedback(
          `Attack Intercepted! Security Decision: ${verifResult.security_decision} (${verifResult.decision_reason})`
        );
      } else {
        setFeedback(
          `Controlled ${type} mutation executed in session database. Proceed to Verification to observe pipeline detection.`
        );
      }
    } catch (err: any) {
      setFeedback(`Threat Simulation Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  if (!sessionId) {
    return (
      <div className="p-8 text-center bg-zaslon-900/60 border border-zaslon-border rounded-xl">
        <h2 className="text-sm font-semibold text-slate-300">No Session Selected</h2>
        <p className="text-xs text-slate-500 mt-1">Please select an active session to test cyber threat detection.</p>
      </div>
    );
  }

  const attackVectors = [
    {
      type: 'FORGERY',
      title: 'Quantum State / Measurement Forgery',
      icon: <Zap className="w-4 h-4 text-amber-400" />,
      badge: 'Quantum Layer Threat',
      description:
        'Manipulates Bob’s quantum measurement outcomes directly in the database. The elevated mismatch ratio (> 2.5%) triggers rejection via Fisher’s Exact Test (p < 0.01).',
      layer: 'Physical / Quantum Circuit',
      consequence: 'Fisher Exact Test rejection with elevated mismatch ratio',
    },
    {
      type: 'INTEGRITY_TAMPERING',
      title: 'Plaintext Message Tampering',
      icon: <FileWarning className="w-4 h-4 text-rose-400" />,
      badge: 'Cryptographic Layer Threat',
      description:
        'Mutates the underlying plaintext message after SHA-512 digest computation. Intercepted via recomputed cryptographic hash comparison before verification.',
      layer: 'Cryptographic Hash Layer',
      consequence: 'SHA-512 integrity failure barrier rejection',
    },
    {
      type: 'REPLAY',
      title: 'Signature Replay Attack',
      icon: <Repeat className="w-4 h-4 text-sky-400" />,
      badge: 'Protocol Layer Threat',
      description:
        'Re-submits an already consumed public declaration signature token across sessions or outside its single-use verification lifecycle.',
      layer: 'Protocol State Engine',
      consequence: 'Anti-replay single-use token consumption barrier',
    },
    {
      type: 'UNAUTHORIZED_VERIFICATION',
      title: 'Unauthorized Verification Attempt',
      icon: <Lock className="w-4 h-4 text-purple-400" />,
      badge: 'Access Control Threat',
      description:
        'An unauthorized entity (Mallory_Attacker) attempts to invoke the verification endpoint without possessing the designated Verifier credential.',
      layer: 'Identity & Access Control',
      consequence: 'Role-based authorization barrier (UNAUTHORIZED decision)',
    },
    {
      type: 'IMPERSONATION',
      title: 'Signer Identity Impersonation',
      icon: <UserX className="w-4 h-4 text-amber-500" />,
      badge: 'Identity Threat',
      description:
        'An adversary attempts to publish declarations claiming the identity of the designated Signer (Eve_Impersonator instead of Alice).',
      layer: 'Declaration Binding',
      consequence: 'Public declaration signer mismatch rejection',
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-100">Cyber Threat Simulation & Detection</h1>
          <p className="text-xs text-slate-400 mt-1">
            Controlled demonstrations of 5 cyber threat classes against real Zaslon-QDS session data.
          </p>
        </div>
        <button
          onClick={fetchAttacks}
          className="px-3 py-1.5 rounded-lg border border-zaslon-border bg-zaslon-850 hover:bg-zaslon-800 text-xs text-slate-300 flex items-center space-x-1.5"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {feedback && (
        <div className="p-3.5 rounded-lg bg-zaslon-850 border border-zaslon-border text-xs font-mono text-slate-200">
          <span className="text-zaslon-quantum font-semibold">FEEDBACK: </span>
          {feedback}
        </div>
      )}

      {/* Live Threat Interception Result Banner */}
      {lastInterception && (
        <div
          className={`p-5 rounded-xl border space-y-2.5 transition-all ${
            lastInterception.security_decision === 'VERIFIED'
              ? 'bg-emerald-950/20 border-emerald-500/40'
              : 'bg-rose-950/20 border-rose-500/40 shadow-lg'
          }`}
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center space-x-2.5">
              <ShieldAlert className="w-5 h-5 text-rose-400" />
              <h3 className="text-sm font-mono font-bold text-slate-100">
                Detection Intercepted: <span className="text-rose-400">{lastInterception.security_decision}</span>
              </h3>
              {lastInterception.attack_detected && (
                <span className="px-2 py-0.5 rounded bg-rose-500/20 text-rose-400 border border-rose-500/30 text-[10px] font-mono font-bold">
                  FLAG: {lastInterception.attack_category}
                </span>
              )}
            </div>

            {onNavigate && (
              <button
                onClick={() => onNavigate('verification')}
                className="text-xs text-zaslon-quantum hover:underline flex items-center space-x-1 font-mono"
              >
                <span>Full Statistical Report</span>
                <ArrowRight className="w-3 h-3" />
              </button>
            )}
          </div>

          <div className="p-3 rounded bg-zaslon-900/80 border border-zaslon-border text-xs font-mono text-slate-200">
            <span className="text-slate-400 font-semibold">REASON: </span>
            {lastInterception.decision_reason}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs font-mono text-slate-400 pt-1">
            <div>
              Mismatch Ratio: <span className="text-rose-400 font-bold">{(lastInterception.mismatch_ratio * 100).toFixed(2)}%</span>
            </div>
            <div>
              Fisher p-value: <span className="text-rose-400 font-bold">{lastInterception.fisher_p_value.toExponential(3)}</span>
            </div>
            <div>
              Statistical Verdict: <span className="text-slate-200 font-bold">{lastInterception.statistical_verdict}</span>
            </div>
          </div>
        </div>
      )}

      {/* 5 Threat Injection Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {attackVectors.map((att) => (
          <div
            key={att.type}
            className="p-5 rounded-xl border border-zaslon-border bg-zaslon-900/60 flex flex-col justify-between space-y-4 hover:border-slate-700 transition-all shadow-sm"
          >
            <div>
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20 font-semibold">
                  {att.badge}
                </span>
                <div className="p-1 rounded bg-zaslon-850 border border-zaslon-border">
                  {att.icon}
                </div>
              </div>
              <h3 className="text-sm font-semibold text-slate-100 mt-2.5">{att.title}</h3>
              <p className="text-xs text-slate-400 mt-1 leading-relaxed">{att.description}</p>
            </div>

            <div className="space-y-2 pt-2 border-t border-zaslon-border/50">
              <button
                onClick={() => runAttack(att.type, true)}
                disabled={loading}
                className="w-full py-2 rounded-lg bg-rose-950/40 hover:bg-rose-900/60 text-rose-300 border border-rose-500/30 text-xs font-semibold transition-colors disabled:opacity-50 flex items-center justify-center space-x-1.5"
              >
                <Bug className="w-3.5 h-3.5" />
                <span>Simulate & Detect Live</span>
              </button>
              <button
                onClick={() => runAttack(att.type, false)}
                disabled={loading}
                className="w-full py-1.5 rounded-lg bg-zaslon-850 hover:bg-zaslon-800 text-slate-400 hover:text-slate-200 border border-zaslon-border text-[11px] font-mono transition-colors disabled:opacity-50"
              >
                Mutate DB State Only
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Session Threat Interception History Log */}
      <div className="p-5 rounded-xl border border-zaslon-border bg-zaslon-900/60 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-mono uppercase tracking-wider text-slate-300 font-semibold flex items-center space-x-2">
            <ShieldAlert className="w-4 h-4 text-rose-400" />
            <span>Session Threat Interception History ({events.length} Events)</span>
          </h3>
          <span className="text-[11px] font-mono text-slate-500">
            Real mutations intercepted by verification engine
          </span>
        </div>

        <div className="space-y-3">
          {events.map((e) => (
            <div
              key={e.id}
              className="p-4 rounded-lg bg-zaslon-850/50 border border-zaslon-border text-xs space-y-2.5 font-mono"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center space-x-2">
                  <span className="px-2 py-0.5 rounded bg-rose-500/20 text-rose-400 border border-rose-500/30 font-bold">
                    {e.attack_type}
                  </span>
                  <span className="text-slate-500 text-[11px]">
                    [{e.simulated ? 'SIMULATED MUTATION' : 'LIVE THREAT'}]
                  </span>
                </div>
                <span className="text-slate-500 text-[10px]">
                  {new Date(e.created_at).toLocaleString()}
                </span>
              </div>

              <div className="p-3 rounded bg-zaslon-950/70 border border-zaslon-border/60 text-slate-300 text-[11px] space-y-1.5">
                <div>
                  <span className="text-slate-500">Attack Vector: </span>
                  <span className="text-slate-200">{e.detection_evidence.attack_vector}</span>
                </div>
                <div>
                  <span className="text-slate-500">Expected Consequence: </span>
                  <span className="text-rose-300">{e.detection_evidence.expected_consequence}</span>
                </div>
                {e.payload_manipulation && Object.keys(e.payload_manipulation).length > 0 && (
                  <div>
                    <span className="text-slate-500">Payload Manipulation: </span>
                    <span className="text-slate-400">{JSON.stringify(e.payload_manipulation)}</span>
                  </div>
                )}
              </div>
            </div>
          ))}

          {events.length === 0 && (
            <div className="text-center py-8 text-xs text-slate-500 font-sans">
              No cyber threat simulations executed for this session yet. Select any attack vector above to demonstrate genuine detection.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
