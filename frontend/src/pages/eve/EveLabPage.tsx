import React, { useState, useEffect } from 'react';
import {
  Radio,
  Skull,
  AlertTriangle,
  Check,
  Send,
  ArrowRight,
  Lock,
  RefreshCw,
  Zap,
  Ban,
  CheckCircle2,
  XCircle,
  FileCode,
  Atom,
  ShieldAlert,
  Activity
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { RoleNavbar } from '../../components/layout/RoleNavbar';
import { ProtocolFlowBar } from '../../components/protocol/ProtocolFlowBar';
import { TransmissionPackage } from '../../types/auth';

export type AttackFamily = 'FAMILY_1_IDENTITY' | 'FAMILY_2_ARTIFACT' | 'FAMILY_3_PROTOCOL' | 'FAMILY_4_QUANTUM';

interface AttackVectorDef {
  id: string;
  name: string;
  family: AttackFamily;
  targetChannel: 'QUANTUM' | 'CLASSICAL' | 'BOTH';
  description: string;
  scientificMechanism: string;
  barrierTriggered: string;
  expectedVerdict: 'REJECTED' | 'UNAUTHORIZED' | 'INTEGRITY_FAILURE';
}

const ATTACK_VECTORS: AttackVectorDef[] = [
  // FAMILY 1: IDENTITY & AUTHORIZATION ATTACKS
  {
    id: 'IMPERSONATION',
    name: '1. Impersonation',
    family: 'FAMILY_1_IDENTITY',
    targetChannel: 'CLASSICAL',
    description: "Modifies declared signer identity to claim Alice's authority from an adversarial identity.",
    scientificMechanism: 'Overrides public declaration signer field to an adversarial identity, violating participant binding.',
    barrierTriggered: 'Barrier 2: Signer Identity Binding Barrier',
    expectedVerdict: 'UNAUTHORIZED'
  },
  {
    id: 'UNAUTHORIZED_VERIFICATION',
    name: '2. Unauthorized Verification',
    family: 'FAMILY_1_IDENTITY',
    targetChannel: 'CLASSICAL',
    description: 'Eve attempts to invoke Bob verification endpoint without designated recipient credentials.',
    scientificMechanism: 'Direct API probe by non-designated verifier caught by authorization guard.',
    barrierTriggered: 'Barrier 1: Verifier Authorization Barrier',
    expectedVerdict: 'UNAUTHORIZED'
  },
  {
    id: 'UNAUTHORIZED_PROBE',
    name: '3. Unauthorized Probe',
    family: 'FAMILY_1_IDENTITY',
    targetChannel: 'BOTH',
    description: 'Eve attempts to query Bob-private sample indices or verification evidence before delivery.',
    scientificMechanism: 'RBAC boundary prevents unauthorized inspection of private quantum sample indices.',
    barrierTriggered: 'Barrier 1: RBAC Verifier Authorization Barrier',
    expectedVerdict: 'UNAUTHORIZED'
  },

  // FAMILY 2: ARTIFACT & INTEGRITY ATTACKS
  {
    id: 'FILE_INTEGRITY_TAMPERING',
    name: '4. File Integrity Tampering',
    family: 'FAMILY_2_ARTIFACT',
    targetChannel: 'CLASSICAL',
    description: 'Mutates original document bytes on disk or in payload after SHA-512 commitment.',
    scientificMechanism: 'Replaces document bytes while retaining original manifest SHA-512 digest, causing hash mismatch.',
    barrierTriggered: 'Barrier 4: Cryptographic SHA-512 File Integrity Barrier',
    expectedVerdict: 'INTEGRITY_FAILURE'
  },
  {
    id: 'DECLARATION_TAMPERING',
    name: '5. Declaration Tampering',
    family: 'FAMILY_2_ARTIFACT',
    targetChannel: 'CLASSICAL',
    description: 'Tampering with signature tokens or declaration hashes inside <filename>.qds.json manifest.',
    scientificMechanism: 'Directly mutates public declaration commitment hash in manifest artifact.',
    barrierTriggered: 'Barrier 3: Public Declaration Commitment Integrity Barrier',
    expectedVerdict: 'INTEGRITY_FAILURE'
  },
  {
    id: 'QDS_PACKAGE_TAMPERING',
    name: '6. QDS Package Tampering',
    family: 'FAMILY_2_ARTIFACT',
    targetChannel: 'CLASSICAL',
    description: 'Substitutes or corrupts committed SHA-512 digest inside the transmission package manifest.',
    scientificMechanism: 'Simulates in-flight man-in-the-middle tampering of the 512-bit message digest.',
    barrierTriggered: 'Barrier 4: Cryptographic SHA-512 File Integrity Barrier',
    expectedVerdict: 'INTEGRITY_FAILURE'
  },
  {
    id: 'FORGERY',
    name: '7. Forgery',
    family: 'FAMILY_2_ARTIFACT',
    targetChannel: 'BOTH',
    description: 'Synthesizes fake signature token and perturbs quantum states without valid entanglement correlation.',
    scientificMechanism: 'Generates forged token without knowing quantum key distribution; triggers state mismatch and Fisher rejection.',
    barrierTriggered: 'Barrier 5: Quantum Teleportation Fisher Exact Test Barrier',
    expectedVerdict: 'REJECTED'
  },

  // FAMILY 3: PROTOCOL ATTACKS
  {
    id: 'REPLAY',
    name: '8. Replay',
    family: 'FAMILY_3_PROTOCOL',
    targetChannel: 'CLASSICAL',
    description: 'Replays an already-consumed single-use public declaration token from a previous verification.',
    scientificMechanism: 'Resubmits previously verified token; blocked by server-authoritative single-use token consumption check.',
    barrierTriggered: 'Barrier 3: Anti-Replay Single-Use Token Barrier',
    expectedVerdict: 'REJECTED'
  },
  {
    id: 'INTERCEPT_AND_RESEND',
    name: '9. Intercept-and-Resend',
    family: 'FAMILY_3_PROTOCOL',
    targetChannel: 'QUANTUM',
    description: 'Eavesdropping interception and state reconstruction inducing non-orthogonal collapse in Bell channel.',
    scientificMechanism: 'Eve intercepts quantum transmission, measures in random bases, and resends reconstructed state.',
    barrierTriggered: 'Barrier 5: Quantum Teleportation Fisher Exact Test Barrier',
    expectedVerdict: 'REJECTED'
  },
  {
    id: 'SESSION_SUBSTITUTION',
    name: '10. Session Substitution',
    family: 'FAMILY_3_PROTOCOL',
    targetChannel: 'CLASSICAL',
    description: 'Splices public declaration token and credentials from a separate, unrelated QDS session into package.',
    scientificMechanism: 'Violates cross-session cryptographic binding between session UUID, verifier, and token.',
    barrierTriggered: 'Barrier 3: Cross-Session Cryptographic Binding Barrier',
    expectedVerdict: 'REJECTED'
  },

  // FAMILY 4: QUANTUM EVIDENCE ATTACKS
  {
    id: 'MEASUREMENT_MANIPULATION',
    name: '11. Measurement Manipulation',
    family: 'FAMILY_4_QUANTUM',
    targetChannel: 'QUANTUM',
    description: "Applies physical Pauli-X bit-flip optical perturbations during in-transit quantum propagation.",
    scientificMechanism: 'Coupled SeQUeNCe and CUDA-Q physical bit-flip rotation on the optical fiber channel, elevating mismatch ratio far beyond 3.00% threshold.',
    barrierTriggered: 'Barrier 5: Quantum Teleportation Fisher Exact Test Barrier',
    expectedVerdict: 'REJECTED'
  },
  {
    id: 'BASIS_MANIPULATION',
    name: '12. Basis Manipulation',
    family: 'FAMILY_4_QUANTUM',
    targetChannel: 'QUANTUM',
    description: 'Induces polarization rotation (pi/4) between Z and X representations in optical stream.',
    scientificMechanism: 'Optical fiber birefringence forces Bob into non-orthogonal conjugate basis measurement, causing high sample mismatch.',
    barrierTriggered: 'Barrier 5: Quantum Teleportation Fisher Exact Test Barrier',
    expectedVerdict: 'REJECTED'
  },
  {
    id: 'QUANTUM_STATE_REPLACEMENT',
    name: '13. Quantum State Replacement',
    family: 'FAMILY_4_QUANTUM',
    targetChannel: 'QUANTUM',
    description: 'Applies phase drift (Pauli-Z) and depolarizing decoherence to quantum channel.',
    scientificMechanism: 'Coupled SeQUeNCe decoherence and CUDA-Q phase rotation, disrupting deferred measurement parity.',
    barrierTriggered: 'Barrier 5: Quantum Teleportation Fisher Exact Test Barrier',
    expectedVerdict: 'REJECTED'
  }
];

export const EveLabPage: React.FC = () => {
  const { user, token } = useAuth();

  // Channel sniffer state
  const [packages, setPackages] = useState<TransmissionPackage[]>([]);
  const [selectedPackage, setSelectedPackage] = useState<TransmissionPackage | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [telemetry, setTelemetry] = useState<any | null>(null);

  // Attack selection state
  const [activeFamily, setActiveFamily] = useState<AttackFamily>('FAMILY_1_IDENTITY');
  const [selectedAttackId, setSelectedAttackId] = useState<string>('IMPERSONATION');

  // Specific attack parameters
  const [affectedCount, setAffectedCount] = useState<number>(600);
  const [spoofedSigner, setSpoofedSigner] = useState<string>('Eve_Malicious_Actor');
  const [spoofedRecipient, setSpoofedRecipient] = useState<string>('Charlie_Attacker');
  const [tamperedPayload, setTamperedPayload] = useState<string>(
    'MALICIOUS ADVERSARY OVERRIDE: Redirect transmission to hostile server node 192.168.99.100'
  );

  // Execution state
  const [isExecuting, setIsExecuting] = useState(false);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [probeResult, setProbeResult] = useState<any | null>(null);

  // One-time action state derivations
  const isIntercepted = selectedPackage?.status === 'INTERCEPTED';
  const isModified = selectedPackage?.status === 'MODIFIED' || Boolean(selectedPackage?.is_tampered);
  const isForwarded = Boolean(
    selectedPackage && ['RECEIVED', 'FORWARDED', 'VERIFIED', 'REJECTED'].includes(selectedPackage.status)
  );

  const canMutate = Boolean(isIntercepted && !isModified && !isForwarded);
  const canPassthrough = Boolean(isIntercepted && !isModified && !isForwarded);
  const canForward = Boolean((isModified || isIntercepted) && !isForwarded);

  // Fetch interceptable transmissions
  const fetchPackages = async () => {
    try {
      const res = await fetch('/api/v1/eve/interceptable', {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data: TransmissionPackage[] = await res.json();
        setPackages(data);
        if (selectedPackage) {
          const updated = data.find((p) => p.id === selectedPackage.id);
          if (updated) setSelectedPackage(updated);
        } else if (data.length > 0) {
          setSelectedPackage(data[0]);
        }
      }
    } catch (err) {
      console.error('Error fetching interceptable transmissions:', err);
    }
  };

  // Fetch channel telemetry for selected package
  const fetchTelemetry = async (pkgId: string) => {
    try {
      const res = await fetch(`/api/v1/eve/channel-telemetry/${pkgId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setTelemetry(data);
      }
    } catch (err) {
      console.error('Error fetching channel telemetry:', err);
    }
  };

  useEffect(() => {
    if (token) {
      fetchPackages();
    }
  }, [token]);

  useEffect(() => {
    if (selectedPackage) {
      setTelemetry(null);
      fetchTelemetry(selectedPackage.id);
    } else {
      setTelemetry(null);
    }
  }, [selectedPackage?.id, selectedPackage?.status, selectedPackage?.is_tampered]);

  // Auto-refresh interval
  useEffect(() => {
    if (!autoRefresh || !token) return;
    const interval = setInterval(fetchPackages, 4000);
    return () => clearInterval(interval);
  }, [autoRefresh, token, selectedPackage?.id]);

  // Action: Intercept
  const handleIntercept = async (pkgId: string) => {
    setIsExecuting(true);
    setActionError(null);
    setActionSuccess(null);
    setProbeResult(null);

    try {
      const res = await fetch(`/api/v1/eve/intercept/${pkgId}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Interception failed');
      }

      const updated: TransmissionPackage = await res.json();
      setSelectedPackage(updated);
      setActionSuccess(`Package #${updated.package_tracking_no} intercepted! Transit to Bob paused.`);
      fetchPackages();
    } catch (err: any) {
      setActionError(err.message || 'Error intercepting transmission');
    } finally {
      setIsExecuting(false);
    }
  };

  // Action: Passthrough
  const handlePassthrough = async () => {
    if (!selectedPackage) return;
    setIsExecuting(true);
    setActionError(null);
    setActionSuccess(null);
    setProbeResult(null);

    try {
      const res = await fetch(`/api/v1/eve/passthrough/${selectedPackage.id}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Passthrough failed');
      }

      const updated: TransmissionPackage = await res.json();
      setSelectedPackage(updated);
      setActionSuccess(`Zero-tamper passthrough set for #${updated.package_tracking_no}. Quantum and classical streams preserved authentic.`);
      fetchPackages();
    } catch (err: any) {
      setActionError(err.message || 'Error executing passthrough');
    } finally {
      setIsExecuting(false);
    }
  };

    // Action: Mutate (Apply any of 13 attacks)
  const handleMutate = async () => {
    if (!selectedPackage) return;

    if (selectedAttackId === 'UNAUTHORIZED_PROBE') {
      await handleProbeVerify();
      return;
    }

    setIsExecuting(true);
    setActionError(null);
    setActionSuccess(null);
    setProbeResult(null);

    let mutationParams: Record<string, any> = {};
    if (
      selectedAttackId === 'MEASUREMENT_MANIPULATION' ||
      selectedAttackId === 'BASIS_MANIPULATION' ||
      selectedAttackId === 'QUANTUM_STATE_REPLACEMENT' ||
      selectedAttackId === 'FORGERY' ||
      selectedAttackId === 'INTERCEPT_AND_RESEND'
    ) {
      mutationParams = { affected_count: affectedCount };
    } else if (selectedAttackId === 'IMPERSONATION') {
      mutationParams = { spoofed_signer: spoofedSigner };
    } else if (selectedAttackId === 'UNAUTHORIZED_VERIFICATION') {
      mutationParams = { spoofed_verifier: spoofedRecipient };
    } else if (selectedAttackId === 'FILE_INTEGRITY_TAMPERING') {
      mutationParams = { tampered_message: tamperedPayload };
    }

    try {
      const res = await fetch(`/api/v1/eve/mutate/${selectedPackage.id}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          attack_type: selectedAttackId,
          mutation_params: mutationParams
        })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Attack injection failed');
      }

      const updated: TransmissionPackage = await res.json();
      setSelectedPackage(updated);
      const attackObj = ATTACK_VECTORS.find((a) => a.id === selectedAttackId);
      setActionSuccess(
        `Attack Injected: [${attackObj?.name || selectedAttackId}]. Transmission mutated on ${
          attackObj?.targetChannel || 'CHANNEL'
        }.`
      );
      fetchPackages();
    } catch (err: any) {
      setActionError(err.message || 'Error mutating transmission');
    } finally {
      setIsExecuting(false);
    }
  };

  // Action: Unauthorized Verification Probe
  const handleProbeVerify = async () => {
    if (!selectedPackage) return;
    setIsExecuting(true);
    setActionError(null);
    setActionSuccess(null);
    setProbeResult(null);

    try {
      const res = await fetch(`/api/v1/eve/probe-verify/${selectedPackage.id}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      });

      const data = await res.json();
      setProbeResult(data);
      if (data.status === 'BLOCKED') {
        setActionSuccess(
          `Probe executed: Verifier Authorization Barrier triggered! Server blocked unauthorized actor '${user?.username}'.`
        );
      } else {
        setActionSuccess('Probe completed.');
      }
      fetchPackages();
    } catch (err: any) {
      setActionError(err.message || 'Error executing unauthorized verification probe');
    } finally {
      setIsExecuting(false);
    }
  };

  // Action: Forward to Bob
  const handleForward = async () => {
    if (!selectedPackage) return;
    setIsExecuting(true);
    setActionError(null);
    setActionSuccess(null);
    setProbeResult(null);

    try {
      const res = await fetch(`/api/v1/eve/forward/${selectedPackage.id}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Forwarding failed');
      }

      const updated: TransmissionPackage = await res.json();
      setSelectedPackage(updated);
      setActionSuccess(
        `Package #${updated.package_tracking_no} dispatched to Bob's inbox. Verification will now evaluate incoming state.`
      );
      fetchPackages();
    } catch (err: any) {
      setActionError(err.message || 'Error forwarding package');
    } finally {
      setIsExecuting(false);
    }
  };

  const currentAttack = ATTACK_VECTORS.find((a) => a.id === selectedAttackId);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <RoleNavbar />
      <ProtocolFlowBar currentRole="EVE" />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Lab Header */}
        <div className="bg-gradient-to-r from-red-950/40 via-purple-950/30 to-slate-900/60 border border-red-500/30 rounded-2xl p-6 shadow-xl relative overflow-hidden">
          <div className="absolute right-0 top-0 translate-x-8 -translate-y-8 w-64 h-64 bg-red-600/10 rounded-full blur-3xl pointer-events-none" />
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center space-x-3">
                <span className="p-2 rounded-lg bg-red-500/20 text-red-400 border border-red-500/30">
                  <Skull className="w-5 h-5" />
                </span>
                <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
                  EVE — Adversary &amp; Interception Laboratory
                </h1>
              </div>
              <p className="text-sm text-slate-300 mt-2 max-w-3xl">
                Eve operates as an active adversary sniffing both the Classical Link and Quantum Optical Fiber.
                Intercept packages, inspect split-screen channel telemetry, inject any of 13 cyber &amp; quantum attack vectors,
                or pass through untouched to Bob.
              </p>
            </div>

            <div className="flex items-center space-x-3">
              <button
                onClick={() => setAutoRefresh(!autoRefresh)}
                className={`px-3 py-1.5 rounded-lg text-xs font-mono font-medium border flex items-center space-x-2 transition ${
                  autoRefresh
                    ? 'bg-red-500/20 text-red-300 border-red-500/40'
                    : 'bg-slate-800 text-slate-400 border-slate-700'
                }`}
              >
                <RefreshCw className={`w-3.5 h-3.5 ${autoRefresh ? 'animate-spin' : ''}`} />
                <span>Sniffer: {autoRefresh ? 'LIVE' : 'PAUSED'}</span>
              </button>
              <button
                onClick={fetchPackages}
                className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono border border-slate-700 flex items-center space-x-1.5"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Refresh</span>
              </button>
            </div>
          </div>
        </div>

        {/* Global Feedback Banners */}
        {actionSuccess && (
          <div className="p-4 rounded-xl bg-emerald-950/50 border border-emerald-500/40 text-emerald-200 flex items-center space-x-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0" />
            <span className="text-sm font-medium">{actionSuccess}</span>
          </div>
        )}
        {actionError && (
          <div className="p-4 rounded-xl bg-red-950/50 border border-red-500/40 text-red-200 flex items-center space-x-3">
            <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0" />
            <span className="text-sm font-medium">{actionError}</span>
          </div>
        )}

        {/* Layout: In-Flight List (Left) vs Sniffer Telemetry & Attack Controls (Right) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Left: In-Flight List (4 cols) */}
          <div className="lg:col-span-4 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold text-slate-100 flex items-center space-x-2">
                <Radio className="w-4 h-4 text-red-400 animate-pulse" />
                <span>Channel Transmissions ({packages.length})</span>
              </h2>
              <span className="text-xs text-slate-500 font-mono">Alice → Bob</span>
            </div>

            {packages.length === 0 ? (
              <div className="p-8 rounded-xl bg-slate-900/60 border border-slate-800 text-center space-y-3">
                <Radio className="w-8 h-8 text-slate-600 mx-auto" />
                <p className="text-sm text-slate-400 font-medium">No packages in transit</p>
                <p className="text-xs text-slate-500">
                  Log in as Alice to sign and dispatch a document across the quantum channel.
                </p>
              </div>
            ) : (
              <div className="space-y-3 max-h-[700px] overflow-y-auto pr-1">
                {packages.map((pkg) => {
                  const isSelected = selectedPackage?.id === pkg.id;
                  return (
                    <div
                      key={pkg.id}
                      onClick={() => setSelectedPackage(pkg)}
                      className={`p-4 rounded-xl border transition cursor-pointer ${
                        isSelected
                          ? 'bg-red-950/30 border-red-500/50 shadow-md'
                          : 'bg-slate-900/70 border-slate-800 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="flex items-center space-x-2">
                            <span className="text-xs font-mono font-bold text-red-300">
                              #{pkg.package_tracking_no}
                            </span>
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase font-bold border ${
                                pkg.status === 'IN_TRANSIT'
                                  ? 'bg-amber-500/20 text-amber-300 border-amber-500/30 animate-pulse'
                                  : pkg.status === 'INTERCEPTED'
                                  ? 'bg-red-500/20 text-red-300 border-red-500/30'
                                  : pkg.status === 'MODIFIED'
                                  ? 'bg-purple-500/20 text-purple-300 border-purple-500/30'
                                  : pkg.status === 'PASSTHROUGH'
                                  ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                                  : 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30'
                              }`}
                            >
                              {pkg.status}
                            </span>
                          </div>
                          <div className="text-xs text-slate-300 font-medium mt-1">
                            {pkg.file_name || 'Plaintext Directive'}
                          </div>
                          <div className="text-[11px] text-slate-400 mt-1 flex items-center space-x-2 font-mono">
                            <span>{pkg.sender_id}</span>
                            <ArrowRight className="w-3 h-3 text-slate-600" />
                            <span>{pkg.recipient_id}</span>
                          </div>
                        </div>

                        {pkg.status === 'IN_TRANSIT' && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleIntercept(pkg.id);
                            }}
                            disabled={isExecuting}
                            className="px-2.5 py-1 rounded bg-red-600 hover:bg-red-500 text-white text-xs font-mono font-semibold flex items-center space-x-1"
                          >
                            <Lock className="w-3 h-3" />
                            <span>Intercept</span>
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Right: Sniffer Telemetry & Attack Controls (8 cols) */}
          <div className="lg:col-span-8 space-y-6">
            {selectedPackage ? (
              <>
                {/* Split-Screen Channel Sniffer */}
                <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-bold font-mono text-slate-200 uppercase tracking-wider flex items-center gap-2">
                      <Activity className="w-4 h-4 text-purple-400" />
                      Dual-Channel Sniffer Stream: #{selectedPackage.package_tracking_no}
                    </h3>
                    <span
                      className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold border ${
                        selectedPackage.is_tampered
                          ? 'bg-red-950 text-red-400 border-red-800'
                          : 'bg-emerald-950 text-emerald-400 border-emerald-800'
                      }`}
                    >
                      {selectedPackage.is_tampered ? `MUTATED [${selectedPackage.attack_type}]` : 'AUTHENTIC CHANNELS'}
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
                    {/* Left: Classical Stream */}
                    <div className="p-4 rounded-lg bg-slate-950 border border-cyan-500/30 space-y-2.5">
                      <div className="flex items-center justify-between border-b border-zaslon-800 pb-2">
                        <span className="text-cyan-400 font-bold uppercase flex items-center gap-1.5">
                          <FileCode className="w-3.5 h-3.5" />
                          Classical Channel
                        </span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800">
                          {telemetry?.classical_channel?.channel_status || 'NORMAL'}
                        </span>
                      </div>
                      <div className="space-y-1.5 text-[11px]">
                        <div className="flex justify-between">
                          <span className="text-slate-500">Document:</span>
                          <span className="text-slate-200 font-semibold truncate max-w-[160px]">
                            {telemetry?.classical_channel?.file_name || selectedPackage.file_name || 'document'}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-500">Size:</span>
                          <span className="text-slate-300">
                            {telemetry?.classical_channel?.file_size_bytes || selectedPackage.file_size_bytes || 0} bytes
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-500">Committed SHA-512:</span>
                          <span
                            className="text-cyan-400 font-mono text-[10px] truncate max-w-[150px]"
                            title={telemetry?.classical_channel?.committed_digest || selectedPackage.committed_digest}
                          >
                            {telemetry?.classical_channel?.committed_digest || selectedPackage.committed_digest}
                          </span>
                        </div>
                        {telemetry?.classical_channel?.current_file_digest && (
                          <div className="flex justify-between items-center bg-red-950/40 p-1.5 rounded border border-red-500/30">
                            <span className="text-red-400 font-semibold text-[10px]">Current File SHA-512:</span>
                            <span
                              className="text-red-300 font-mono text-[10px] truncate max-w-[140px]"
                              title={telemetry.classical_channel.current_file_digest}
                            >
                              {telemetry.classical_channel.current_file_digest.slice(0, 16)}... (TAMPERED)
                            </span>
                          </div>
                        )}
                        <div className="flex justify-between">
                          <span className="text-slate-500">Signature Token:</span>
                          <span className="text-emerald-400 truncate max-w-[150px]">
                            {telemetry?.classical_channel?.signature_token || selectedPackage.signature_token}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-500">Transport:</span>
                          <span className="text-slate-400">Application-Level Classical Transmission</span>
                        </div>
                      </div>
                    </div>

                    {/* Right: Quantum Stream */}
                    <div className="p-4 rounded-lg bg-slate-950 border border-purple-500/30 space-y-2.5">
                      <div className="flex items-center justify-between border-b border-zaslon-800 pb-2">
                        <span className="text-purple-400 font-bold uppercase flex items-center gap-1.5">
                          <Atom className="w-3.5 h-3.5" />
                          Quantum Fiber Channel
                        </span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-purple-950 text-purple-300 border border-purple-800">
                          {telemetry?.quantum_channel?.channel_status || 'COHERENT'}
                        </span>
                      </div>
                      <div className="space-y-1.5 text-[11px]">
                        <div className="flex justify-between">
                          <span className="text-slate-500">Teleportation Ops:</span>
                          <span className="text-purple-300 font-semibold">4,096 circuits</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-500">Physical Qubits:</span>
                          <span className="text-slate-300">12,288 qubits (Q0, Q1, Q2)</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-500">Fiber Topology:</span>
                          <span className="text-slate-300">25.0 km • 0.20 dB/km loss</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-500">Propagation Delay:</span>
                          <span className="text-slate-300">122.5 µs (Discrete-Event)</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-500">Entanglement Fidelity:</span>
                          <span
                            className={`font-semibold ${
                              selectedPackage.is_tampered ? 'text-red-400' : 'text-emerald-400'
                            }`}
                          >
                            {selectedPackage.is_tampered ? '0.720 (Perturbed)' : '0.991 (Authentic)'}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* 13 Cyber & Quantum Attack Vectors Laboratory */}
                <div className="bg-slate-900/80 border border-red-500/30 rounded-xl p-5 space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-bold font-mono text-red-400 uppercase tracking-wider flex items-center gap-2">
                      <ShieldAlert className="w-4 h-4" />
                      Cyber &amp; Quantum Threat Manipulation Catalog (13 Vectors)
                    </h3>
                  </div>

                  {/* 4 Attack Family Tabs */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs font-mono">
                    <button
                      type="button"
                      onClick={() => setActiveFamily('FAMILY_1_IDENTITY')}
                      className={`px-3 py-2 rounded-lg border text-left transition ${
                        activeFamily === 'FAMILY_1_IDENTITY'
                          ? 'bg-amber-900/40 text-amber-300 border-amber-500/50 font-bold'
                          : 'bg-slate-950 text-slate-400 border-slate-800 hover:border-slate-700'
                      }`}
                    >
                      <div className="text-[10px] text-slate-500 uppercase">Family 1</div>
                      <div className="font-semibold">Identity &amp; Auth (3)</div>
                    </button>
                    <button
                      type="button"
                      onClick={() => setActiveFamily('FAMILY_2_ARTIFACT')}
                      className={`px-3 py-2 rounded-lg border text-left transition ${
                        activeFamily === 'FAMILY_2_ARTIFACT'
                          ? 'bg-cyan-900/40 text-cyan-300 border-cyan-500/50 font-bold'
                          : 'bg-slate-950 text-slate-400 border-slate-800 hover:border-slate-700'
                      }`}
                    >
                      <div className="text-[10px] text-slate-500 uppercase">Family 2</div>
                      <div className="font-semibold">Artifact &amp; Integrity (4)</div>
                    </button>
                    <button
                      type="button"
                      onClick={() => setActiveFamily('FAMILY_3_PROTOCOL')}
                      className={`px-3 py-2 rounded-lg border text-left transition ${
                        activeFamily === 'FAMILY_3_PROTOCOL'
                          ? 'bg-red-900/40 text-red-300 border-red-500/50 font-bold'
                          : 'bg-slate-950 text-slate-400 border-slate-800 hover:border-slate-700'
                      }`}
                    >
                      <div className="text-[10px] text-slate-500 uppercase">Family 3</div>
                      <div className="font-semibold">Protocol (3)</div>
                    </button>
                    <button
                      type="button"
                      onClick={() => setActiveFamily('FAMILY_4_QUANTUM')}
                      className={`px-3 py-2 rounded-lg border text-left transition ${
                        activeFamily === 'FAMILY_4_QUANTUM'
                          ? 'bg-purple-900/40 text-purple-300 border-purple-500/50 font-bold'
                          : 'bg-slate-950 text-slate-400 border-slate-800 hover:border-slate-700'
                      }`}
                    >
                      <div className="text-[10px] text-slate-500 uppercase">Family 4</div>
                      <div className="font-semibold">Quantum Evidence (3)</div>
                    </button>
                  </div>

                  {/* Attack List within active family */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {ATTACK_VECTORS.filter((a) => a.family === activeFamily).map((atk) => {
                      const isSelected = selectedAttackId === atk.id;
                      return (
                        <div
                          key={atk.id}
                          onClick={() => {
                            if (canMutate) {
                              setSelectedAttackId(atk.id);
                            }
                          }}
                          className={`p-3 rounded-lg border transition ${
                            !canMutate ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
                          } ${
                            isSelected
                              ? 'bg-red-950/40 border-red-500 text-white shadow-md'
                              : 'bg-slate-950 border-slate-800 hover:border-slate-700 text-slate-300'
                          }`}
                        >
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-bold text-xs font-mono">{atk.name}</span>
                            <span
                              className={`text-[9px] font-mono px-1.5 py-0.5 rounded border ${
                                atk.expectedVerdict === 'REJECTED'
                                  ? 'bg-red-950 text-red-400 border-red-800'
                                  : atk.expectedVerdict === 'UNAUTHORIZED'
                                  ? 'bg-amber-950 text-amber-400 border-amber-800'
                                  : 'bg-purple-950 text-purple-400 border-purple-800'
                              }`}
                            >
                              {atk.expectedVerdict}
                            </span>
                          </div>
                          <p className="text-[11px] text-slate-400 line-clamp-2">{atk.description}</p>
                        </div>
                      );
                    })}
                  </div>

                  {/* Selected Attack Details & Mutation Parameters */}
                  {currentAttack && (
                    <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-xs font-mono space-y-3">
                      <div className="border-b border-slate-800 pb-2">
                        <div className="text-slate-200 font-bold text-sm">{currentAttack.name}</div>
                        <div className="text-[11px] text-slate-400 mt-0.5">{currentAttack.scientificMechanism}</div>
                        <div className="text-[10px] text-red-400 mt-1">
                          Triggers: <span className="text-slate-300">{currentAttack.barrierTriggered}</span>
                        </div>
                      </div>

                      {/* Dynamic Parameters */}
                      {(currentAttack.id === 'MEASUREMENT_MANIPULATION' ||
                        currentAttack.id === 'BASIS_MANIPULATION' ||
                        currentAttack.id === 'QUANTUM_STATE_REPLACEMENT' ||
                        currentAttack.id === 'FORGERY' ||
                        currentAttack.id === 'INTERCEPT_AND_RESEND') && (
                        <div>
                          <label className="block text-slate-400 mb-1">
                            Affected Teleportation Operations: <span className="text-cyan-400 font-bold">{affectedCount} / 4,096</span>
                          </label>
                          <input
                            type="range"
                            min="50"
                            max="2000"
                            step="50"
                            value={affectedCount}
                            onChange={(e) => setAffectedCount(Number(e.target.value))}
                            className="w-full accent-cyan-400"
                          />
                        </div>
                      )}

                      {currentAttack.id === 'IMPERSONATION' && (
                        <div>
                          <label className="block text-slate-400 mb-1">Spoofed Signer Identity</label>
                          <input
                            type="text"
                            value={spoofedSigner}
                            onChange={(e) => setSpoofedSigner(e.target.value)}
                            className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-slate-100"
                          />
                        </div>
                      )}

                      {currentAttack.id === 'UNAUTHORIZED_VERIFICATION' && (
                        <div>
                          <label className="block text-slate-400 mb-1">Spoofed Destination Recipient</label>
                          <input
                            type="text"
                            value={spoofedRecipient}
                            onChange={(e) => setSpoofedRecipient(e.target.value)}
                            className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-slate-100"
                          />
                        </div>
                      )}

                      {currentAttack.id === 'UNAUTHORIZED_PROBE' && (
                        <div className="p-2.5 rounded bg-amber-950/30 border border-amber-500/30 text-amber-300 text-[11px]">
                          Direct probe against Bob-private verification resource (/verification/:id/samples). Server will return HTTP 403 Forbidden and log an immutable intrusion event.
                        </div>
                      )}

                      {currentAttack.id === 'FILE_INTEGRITY_TAMPERING' && (
                        <div>
                          <label className="block text-slate-400 mb-1">Mutated Document Payload</label>
                          <textarea
                            rows={2}
                            value={tamperedPayload}
                            onChange={(e) => setTamperedPayload(e.target.value)}
                            className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-slate-100 text-xs"
                          />
                        </div>
                      )}
                    </div>
                  )}

                  {/* Status Feedback Banners */}
                  {selectedPackage.status === 'IN_TRANSIT' && (
                    <div className="p-3 rounded-lg bg-amber-950/40 border border-amber-500/40 text-amber-200 text-xs font-mono flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Lock className="w-4 h-4 text-amber-400" />
                        <span>TRANSMISSION IN TRANSIT: Intercept transmission to pause transit and enable attack controls.</span>
                      </div>
                      <button
                        type="button"
                        onClick={() => handleIntercept(selectedPackage.id)}
                        disabled={isExecuting}
                        className="px-3 py-1 rounded bg-red-600 hover:bg-red-500 text-white text-xs font-bold transition flex items-center gap-1"
                      >
                        <Lock className="w-3 h-3" />
                        <span>Intercept</span>
                      </button>
                    </div>
                  )}

                  {isModified && !isForwarded && (
                    <div className="p-3 rounded-lg bg-purple-950/50 border border-purple-500/50 text-purple-200 text-xs font-mono flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Zap className="w-4 h-4 text-purple-400 animate-pulse" />
                        <span>ATTACK EXECUTED: <strong className="text-white">[{selectedPackage.attack_type || selectedAttackId}]</strong> — 1-attack limit enforced. Ready to forward to Bob.</span>
                      </div>
                      <span className="text-[10px] px-2 py-0.5 rounded bg-purple-900/60 text-purple-300 border border-purple-600 font-bold uppercase">Ready to Forward</span>
                    </div>
                  )}

                  {isForwarded && (
                    <div className="p-3 rounded-lg bg-slate-950 border border-cyan-500/40 text-cyan-200 text-xs font-mono flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Send className="w-4 h-4 text-cyan-400" />
                        <span>STATUS: FORWARDED TO BOB'S INBOX — Channel transmission complete (Read-Only).</span>
                      </div>
                      <span className="text-[10px] px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-700 font-bold uppercase">{selectedPackage.status}</span>
                    </div>
                  )}

                  {/* Actions Bar */}
                  <div className="flex flex-wrap gap-3 pt-2">
                    <button
                      type="button"
                      onClick={handleMutate}
                      disabled={isExecuting || !canMutate}
                      className="flex-1 py-2.5 px-4 rounded-lg bg-red-600 hover:bg-red-500 text-white font-mono text-xs font-bold transition flex items-center justify-center gap-2 disabled:opacity-30 disabled:cursor-not-allowed"
                    >
                      <Zap className="w-4 h-4" />
                      <span>INJECT ATTACK MUTATION (ONE-TIME)</span>
                    </button>

                    <button
                      type="button"
                      onClick={handlePassthrough}
                      disabled={isExecuting || !canPassthrough}
                      className="py-2.5 px-4 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-mono text-xs font-bold transition flex items-center justify-center gap-2 disabled:opacity-30 disabled:cursor-not-allowed"
                    >
                      <Check className="w-4 h-4" />
                      <span>PASSTHROUGH (UNTOUCHED)</span>
                    </button>

                    <button
                      type="button"
                      onClick={handleForward}
                      disabled={isExecuting || !canForward}
                      className={`py-2.5 px-4 rounded-lg text-white font-mono text-xs font-bold transition flex items-center justify-center gap-2 ${
                        canForward && isModified
                          ? 'bg-gradient-to-r from-purple-600 to-cyan-600 hover:from-purple-500 hover:to-cyan-500 shadow-lg animate-pulse'
                          : 'bg-cyan-600 hover:bg-cyan-500'
                      } disabled:opacity-30 disabled:cursor-not-allowed disabled:animate-none`}
                    >
                      <Send className="w-4 h-4" />
                      <span>FORWARD TO BOB'S INBOX</span>
                    </button>

                    <button
                      type="button"
                      onClick={handleProbeVerify}
                      disabled={isExecuting}
                      className="py-2.5 px-3 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-amber-300 font-mono text-xs transition flex items-center gap-1.5"
                    >
                      <Ban className="w-3.5 h-3.5" />
                      <span>Probe Verify</span>
                    </button>
                  </div>

                  {/* Probe Result Banner */}
                  {probeResult && (
                    <div className="p-4 rounded-xl bg-amber-950/40 border border-amber-500/40 text-amber-200 text-xs font-mono space-y-1">
                      <div className="font-bold flex items-center gap-2">
                        <XCircle className="w-4 h-4 text-amber-400" />
                        <span>Security Barrier Triggered: {probeResult.barrier_triggered}</span>
                      </div>
                      <div>Verdict: <span className="font-semibold text-white">{probeResult.security_verdict}</span></div>
                      <div className="text-amber-300/80 text-[11px]">{probeResult.reason}</div>
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div className="p-12 rounded-xl bg-slate-900/60 border border-slate-800 text-center space-y-3">
                <Skull className="w-12 h-12 text-slate-600 mx-auto" />
                <h3 className="text-base font-medium text-slate-300">No Transmission Selected</h3>
                <p className="text-xs text-slate-500 max-w-sm mx-auto">
                  Select an in-flight package from the sniffer column to inspect its dual-channel telemetry and stage attacks.
                </p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};
