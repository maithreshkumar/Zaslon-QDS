import React, { useState, useEffect, useRef } from 'react';
import {
  Inbox,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  RefreshCw,
  Atom,
  Lock,
  Check,
  Layers,
  ChevronRight,
  Upload,
  Download,
  FileCheck,
  FileCode,
  Award,
  ShieldAlert
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { RoleNavbar } from '../../components/layout/RoleNavbar';
import { ProtocolFlowBar } from '../../components/protocol/ProtocolFlowBar';
import { TransmissionPackage } from '../../types/auth';

interface VerificationEvidence {
  verification_id: string;
  session_id: string;
  tracking_no: string;
  security_decision: string;
  statistical_verdict: string;
  attack_detected: boolean;
  attack_category: string | null;
  decision_reason: string;
  verified_at: string;
  statistical_evidence: {
    sample_size: number;
    match_count: number;
    mismatch_count: number;
    mismatch_ratio: number;
    mismatch_ratio_percent: string;
    threshold_ratio: number;
    threshold_ratio_percent: string;
    fisher_p_value: number;
    fisher_odds_ratio: number;
    odds_ratio_display: string;
    baseline_error_rate: number;
    significance_alpha: number;
    contingency_table: number[][];
  };
  defense_barriers: {
    barrier_name: string;
    threat_checked: string;
    status: 'PASSED' | 'FAILED';
    detail: string;
  }[];
}

const VERIFICATION_STEPS = [
  { step: 1, name: 'Verifier Authentication Check', desc: 'Validates caller identity against system auth directory' },
  { step: 2, name: 'Verifier Authorization Barrier', desc: 'Enforces caller is designated session recipient (Bob)' },
  { step: 3, name: 'QDS Package Schema & Version', desc: 'Validates JSON package manifest structural format' },
  { step: 4, name: 'Package Integrity Commitment', desc: 'Verifies tracking number matches manifest envelope' },
  { step: 5, name: 'Session & Cryptographic Binding', desc: 'Verifies session UUID and verifier cross-binding' },
  { step: 6, name: 'Signer Identity Binding', desc: 'Validates declaration signer matches authentic session author' },
  { step: 7, name: 'Streaming SHA-512 File Rehash', desc: 'Recomputes streaming 64KB digest from document bytes' },
  { step: 8, name: 'Declaration Existence & Commitment', desc: 'Verifies sealed public declaration and payload hash' },
  { step: 9, name: 'Anti-Replay & Freshness Window', desc: 'Enforces unconsumed declaration token and 300s freshness window' },
  { step: 10, name: 'Quantum Telemetry Completeness', desc: 'Validates 4,096 CUDA-Q teleportation operations completed' },
  { step: 11, name: 'Deterministic State Schedule', desc: 'Expands SHA-512 to reference state and basis schedule' },
  { step: 12, name: 'Private 5% Seeded Sampling', desc: 'Deterministic pseudo-random selection of ~205 sample operations' },
  { step: 13, name: 'Sample Mismatch Ratio Barrier', desc: 'Evaluates sample error rate against 3.00% security threshold' },
  { step: 14, name: "Hypergeometric Fisher's Test", desc: 'Calculates exact p-value against 1.00% authentic channel baseline' },
  { step: 15, name: 'Threat Classification & Retirement', desc: 'Determines explainable verdict and atomically burns token' }
];

export const BobPortalPage: React.FC = () => {
  const { user, token } = useAuth();
  const manualFileInputRef = useRef<HTMLInputElement>(null);
  const manualQdsInputRef = useRef<HTMLInputElement>(null);

  const [activeTab, setActiveTab] = useState<'inbox' | 'manual' | 'history' | 'alerts'>('inbox');
  const [inboxPackages, setInboxPackages] = useState<TransmissionPackage[]>([]);
  const [selectedPackage, setSelectedPackage] = useState<TransmissionPackage | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [securityEvents, setSecurityEvents] = useState<any[]>([]);

  // Manual Upload Verification State
  const [manualDocFile, setManualDocFile] = useState<File | null>(null);
  const [manualQdsFile, setManualQdsFile] = useState<File | null>(null);

  // Verification state
  const [sampleRatio, setSampleRatio] = useState<number>(0.05);
  const [isVerifying, setIsVerifying] = useState(false);
  const [detailedEvidence, setDetailedEvidence] = useState<VerificationEvidence | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Verification history
  const [historyList, setHistoryList] = useState<any[]>([]);

  // Fetch Bob's inbox
  const fetchInbox = async () => {
    setIsLoading(true);
    try {
      const res = await fetch('/api/v1/bob/inbox', {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data: TransmissionPackage[] = await res.json();
        setInboxPackages(data);
        if (selectedPackage) {
          const updated = data.find((p) => p.id === selectedPackage.id);
          if (updated) setSelectedPackage(updated);
        } else if (data.length > 0) {
          setSelectedPackage(data[0]);
        }
      }
    } catch (err) {
      console.error('Error fetching Bob inbox:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      fetchInbox();
      fetchSecurityEvents();
    }
  }, [token]);

  // Fetch verifications history
  const fetchHistory = async () => {
    try {
      const res = await fetch('/api/v1/bob/verifications', {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setHistoryList(data);
      }
    } catch (err) {
      console.error('Error fetching verification history:', err);
    }
  };

  // Fetch security intrusion events (e.g. unauthorized probes)
  const fetchSecurityEvents = async () => {
    try {
      const res = await fetch('/api/v1/bob/security-events', {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setSecurityEvents(data);
      }
    } catch (err) {
      console.error('Error fetching security events:', err);
    }
  };

  useEffect(() => {
    if (token && activeTab === 'history') {
      fetchHistory();
    }
    if (token && activeTab === 'alerts') {
      fetchSecurityEvents();
    }
  }, [token, activeTab]);

  // Rehydrate stored verification evidence whenever selectedPackage changes
  useEffect(() => {
    let isMounted = true;
    if (!selectedPackage || !token) {
      setDetailedEvidence(null);
      return;
    }

    const loadPackageVerification = async () => {
      fetchSecurityEvents();
      try {
        const res = await fetch(`/api/v1/bob/inbox/${selectedPackage.id}/verification`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          if (isMounted) {
            if (data.has_verification && data.evidence) {
              setDetailedEvidence(data.evidence);
            } else {
              setDetailedEvidence(null);
            }
          }
        }
      } catch (err) {
        console.error('Failed to load verification for package:', err);
      }
    };

    loadPackageVerification();
    return () => {
      isMounted = false;
    };
  }, [selectedPackage?.id, token]);

  const isAlreadyVerified = Boolean(
    selectedPackage && (
      selectedPackage.status === 'VERIFIED' ||
      selectedPackage.status === 'REJECTED' ||
      detailedEvidence !== null
    )
  );

  // Execute Zaslon-QDS Verification for Inbox Package
  const handleExecuteVerification = async () => {
    if (!selectedPackage) return;
    setIsVerifying(true);
    setError(null);
    setDetailedEvidence(null);

    try {
      const res = await fetch(`/api/v1/bob/inbox/${selectedPackage.id}/verify`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          sample_ratio: sampleRatio
        })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Verification failed');
      }

      const result = await res.json();

      // Fetch rich explainability evidence
      if (result.id) {
        const evidenceRes = await fetch(`/api/v1/bob/verifications/${result.id}/evidence`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (evidenceRes.ok) {
          const evidenceData = await evidenceRes.json();
          setDetailedEvidence(evidenceData);
        }
      }

      // Refresh inbox
      fetchInbox();
    } catch (err: any) {
      setError(err.message || 'Error executing verification');
    } finally {
      setIsVerifying(false);
    }
  };

  // Execute Manual Dual-File Upload Verification
  const handleManualUploadVerify = async () => {
    if (!manualDocFile || !manualQdsFile) {
      setError('Please provide both the signed document file and the companion .qds.json package.');
      return;
    }

    setIsVerifying(true);
    setError(null);
    setDetailedEvidence(null);

    try {
      const formData = new FormData();
      formData.append('file', manualDocFile);
      formData.append('qds_file', manualQdsFile);

      const res = await fetch('/api/v1/bob/manual-verify', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Manual verification failed');
      }

      const result = await res.json();

      if (result.id) {
        const evidenceRes = await fetch(`/api/v1/bob/verifications/${result.id}/evidence`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (evidenceRes.ok) {
          const evidenceData = await evidenceRes.json();
          setDetailedEvidence(evidenceData);
        }
      }
    } catch (err: any) {
      setError(err.message || 'Error executing manual upload verification');
    } finally {
      setIsVerifying(false);
    }
  };

  // Download Cryptographic Certificate Receipt (.cert.json)
  const handleDownloadCertificate = async (verificationId: string) => {
    try {
      const res = await fetch(`/api/v1/bob/verifications/${verificationId}/certificate`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!res.ok) throw new Error('Failed to download verification certificate');
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `qds_verification_${verificationId.slice(0, 8)}.cert.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (err: any) {
      setError(err.message || 'Error downloading certificate');
    }
  };

  // Download Inbox Document File
  const handleDownloadInboxFile = async (pkgId: string, filename?: string) => {
    try {
      const res = await fetch(`/api/v1/bob/files/${pkgId}/download`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!res.ok) throw new Error('Failed to download document');
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename || 'document';
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (err: any) {
      setError(err.message || 'Error downloading document');
    }
  };

  // Download Inbox .qds.json package
  const handleDownloadInboxQds = async (pkgId: string, filename?: string) => {
    try {
      const res = await fetch(`/api/v1/bob/packages/${pkgId}/qds-json`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!res.ok) throw new Error('Failed to download .qds.json package');
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${filename || 'document'}.qds.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (err: any) {
      setError(err.message || 'Error downloading .qds.json package');
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <RoleNavbar />
      <ProtocolFlowBar currentRole="BOB" />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Verifier Header */}
        <div className="bg-gradient-to-r from-emerald-950/40 via-cyan-950/30 to-slate-900/60 border border-emerald-500/30 rounded-2xl p-6 shadow-xl relative overflow-hidden">
          <div className="absolute right-0 top-0 translate-x-8 -translate-y-8 w-64 h-64 bg-emerald-600/10 rounded-full blur-3xl pointer-events-none" />
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center space-x-3">
                <span className="p-2 rounded-lg bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                  <ShieldCheck className="w-5 h-5" />
                </span>
                <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
                  BOB — Verifier &amp; Security Decision Suite
                </h1>
              </div>
              <p className="text-sm text-slate-300 mt-2 max-w-3xl">
                Bob is the designated recipient and autonomous cryptographic verifier. Verify in-flight packages received
                across the dual classical/quantum transmission channels or manually upload offline files with companion .qds.json bundles.
              </p>
            </div>

            <div className="flex items-center space-x-3">
              <div className="flex rounded-lg bg-slate-900 p-1 border border-slate-800 text-xs font-mono">
                <button
                  onClick={() => {
                    setActiveTab('inbox');
                    setDetailedEvidence(null);
                  }}
                  className={`px-3 py-1.5 rounded-md font-semibold transition ${
                    activeTab === 'inbox' ? 'bg-emerald-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Inbox ({inboxPackages.length})
                </button>
                <button
                  onClick={() => {
                    setActiveTab('manual');
                    setDetailedEvidence(null);
                  }}
                  className={`px-3 py-1.5 rounded-md font-semibold transition ${
                    activeTab === 'manual' ? 'bg-cyan-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Manual Upload
                </button>
                <button
                  onClick={() => setActiveTab('history')}
                  className={`px-3 py-1.5 rounded-md font-semibold transition ${
                    activeTab === 'history' ? 'bg-emerald-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Ledger ({historyList.length})
                </button>
                <button
                  onClick={() => {
                    setActiveTab('alerts');
                    setDetailedEvidence(null);
                  }}
                  className={`px-3 py-1.5 rounded-md font-semibold transition flex items-center gap-1.5 ${
                    activeTab === 'alerts' ? 'bg-amber-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <ShieldAlert className="w-3.5 h-3.5" />
                  <span>Alerts ({securityEvents.length})</span>
                </button>
              </div>

              <button
                onClick={fetchInbox}
                className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono border border-slate-700 flex items-center space-x-1.5"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
                <span>Refresh</span>
              </button>
            </div>
          </div>
        </div>

        {error && (
          <div className="p-4 rounded-xl bg-red-950/50 border border-red-500/40 text-red-200 flex items-center space-x-3 text-xs font-mono">
            <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0" />
            <span className="font-medium">{error}</span>
          </div>
        )}

        {/* Tab 1: In-Flight Transmissions Inbox */}
        {activeTab === 'inbox' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
            {/* Left Column: Inbox List (4 cols) */}
            <div className="lg:col-span-4 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-base font-semibold text-slate-100 flex items-center space-x-2">
                  <Inbox className="w-4 h-4 text-emerald-400" />
                  <span>Incoming Packages ({inboxPackages.length})</span>
                </h2>
                <span className="text-xs text-slate-500 font-mono">Designated: {user?.username}</span>
              </div>

              {inboxPackages.length === 0 ? (
                <div className="p-8 rounded-xl bg-slate-900/60 border border-slate-800 text-center space-y-3">
                  <Inbox className="w-8 h-8 text-slate-600 mx-auto" />
                  <p className="text-sm text-slate-400 font-medium">Inbox is empty</p>
                  <p className="text-xs text-slate-500">
                    Alice must sign and dispatch a package, or Eve must forward an in-flight transmission to Bob.
                  </p>
                </div>
              ) : (
                <div className="space-y-3 max-h-[640px] overflow-y-auto pr-1">
                  {inboxPackages.map((pkg) => {
                    const isSelected = selectedPackage?.id === pkg.id;
                    return (
                      <div
                        key={pkg.id}
                        onClick={() => {
                          setSelectedPackage(pkg);
                        }}
                        className={`p-4 rounded-xl border transition cursor-pointer ${
                          isSelected
                            ? 'bg-emerald-950/30 border-emerald-500/50 shadow-md'
                            : 'bg-slate-900/70 border-slate-800 hover:border-slate-700'
                        }`}
                      >
                        <div className="flex items-start justify-between">
                          <div className="space-y-1">
                            <span className="text-xs font-mono font-bold text-emerald-300">
                              #{pkg.package_tracking_no}
                            </span>
                            <div className="text-xs text-slate-200 font-semibold truncate max-w-[180px]">
                              {pkg.file_name || 'Plaintext Directive'}
                            </div>
                            <div className="text-[11px] text-slate-400 flex items-center space-x-1.5 font-mono">
                              <span>From: {pkg.sender_id}</span>
                            </div>
                          </div>
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase font-bold border ${
                              pkg.status === 'VERIFIED'
                                ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                                : pkg.status === 'REJECTED'
                                ? 'bg-red-500/20 text-red-300 border-red-500/30'
                                : 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30'
                            }`}
                          >
                            {pkg.status}
                          </span>
                        </div>

                        <div className="mt-2 flex items-center justify-between text-[11px] text-slate-500 font-mono">
                          <span>{new Date(pkg.created_at).toLocaleTimeString()}</span>
                          <span className="text-cyan-400 font-semibold flex items-center">
                            Inspect <ChevronRight className="w-3 h-3 ml-0.5" />
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Right Column: Inspection & Verification Execution (8 cols) */}
            <div className="lg:col-span-8 space-y-6">
              {selectedPackage ? (
                <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-6 shadow-xl">
                  {/* Manifest Header */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-800 gap-2">
                    <div>
                      <div className="flex items-center space-x-2">
                        <h3 className="text-lg font-bold text-white font-mono">
                          Package #{selectedPackage.package_tracking_no}
                        </h3>
                        <span
                          className={`px-2.5 py-0.5 rounded-full text-xs font-mono uppercase font-bold border ${
                            selectedPackage.status === 'VERIFIED'
                              ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40'
                              : selectedPackage.status === 'REJECTED'
                              ? 'bg-red-500/20 text-red-400 border-red-500/40'
                              : 'bg-cyan-500/20 text-cyan-400 border-cyan-500/40'
                          }`}
                        >
                          {selectedPackage.status}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 mt-1 font-mono">
                        File: <span className="text-slate-200 font-semibold">{selectedPackage.file_name || 'directive.txt'}</span>
                      </p>
                    </div>

                    {/* Offline Artifact Downloads */}
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => handleDownloadInboxQds(selectedPackage.id, selectedPackage.file_name)}
                        className="px-3 py-1.5 rounded-lg bg-slate-950 hover:bg-slate-800 border border-slate-700 text-cyan-300 font-mono text-xs flex items-center gap-1.5 transition"
                      >
                        <Download className="w-3.5 h-3.5" />
                        <span>.qds.json</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDownloadInboxFile(selectedPackage.id, selectedPackage.file_name)}
                        className="px-3 py-1.5 rounded-lg bg-slate-950 hover:bg-slate-800 border border-slate-700 text-slate-300 font-mono text-xs flex items-center gap-1.5 transition"
                      >
                        <Download className="w-3.5 h-3.5" />
                        <span>Document</span>
                      </button>
                    </div>
                  </div>

                  {/* Cryptographic Manifest Details */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs font-mono">
                    <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 space-y-1 sm:col-span-2">
                      <span className="text-slate-500 block">COMMITTED SHA-512 MESSAGE DIGEST</span>
                      <span className="text-cyan-400 break-all text-[11px]">{selectedPackage.committed_digest}</span>
                    </div>
                    <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 space-y-1">
                      <span className="text-slate-500 block">PUBLIC DECLARATION SIGNATURE TOKEN</span>
                      <span className="text-purple-400 break-all text-[11px]">{selectedPackage.signature_token}</span>
                    </div>
                    <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 space-y-1">
                      <span className="text-slate-500 block">QUANTUM RUN BINDING</span>
                      <span className="text-emerald-400 break-all text-[11px]">
                        {selectedPackage.quantum_run_id || 'CUDA-Q Run Attached'}
                      </span>
                    </div>
                  </div>

                  {/* Security Intrusion & Unauthorized Access Alerts for Selected Package */}
                  {(() => {
                    const pkgAlerts = securityEvents.filter(
                      (e) => e.session_id === selectedPackage.session_id ||
                             e.details?.package_tracking_no === selectedPackage.package_tracking_no ||
                             e.resource?.includes(selectedPackage.id)
                    );
                    if (pkgAlerts.length === 0) return null;
                    return (
                      <div className="space-y-3">
                        {pkgAlerts.map((evt) => (
                          <div
                            key={evt.id}
                            className="p-4 rounded-xl bg-amber-950/40 border border-amber-500/50 space-y-2 font-mono shadow-md"
                          >
                            <div className="flex items-center justify-between border-b border-amber-500/30 pb-2">
                              <div className="flex items-center space-x-2 text-amber-400 font-bold text-xs">
                                <ShieldAlert className="w-4 h-4" />
                                <span>SECURITY EVENT: {evt.event_type}</span>
                              </div>
                              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-900/80 border border-amber-500/60 text-amber-200 uppercase">
                                Outcome: {evt.details?.outcome || 'BLOCKED (HTTP 403)'}
                              </span>
                            </div>
                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px]">
                              <div>
                                <span className="text-slate-500">Actor: </span>
                                <span className="text-red-300 font-bold">{evt.actor}</span>
                              </div>
                              <div>
                                <span className="text-slate-500">Target: </span>
                                <span className="text-slate-200 truncate">{evt.details?.target || evt.resource}</span>
                              </div>
                              <div>
                                <span className="text-slate-500">HTTP: </span>
                                <span className="text-amber-300 font-bold">403 Forbidden</span>
                              </div>
                              <div>
                                <span className="text-slate-500">Timestamp: </span>
                                <span className="text-slate-400">
                                  {evt.created_at ? new Date(evt.created_at).toLocaleTimeString() : 'N/A'}
                                </span>
                              </div>
                            </div>
                            <p className="text-[11px] text-amber-200/90 pt-1">
                              {evt.details?.message || evt.details?.mechanism ||
                                'An adversary attempted unauthorized access or verification on this transmission. The attempt was denied by the security barrier. The underlying document and quantum signatures remain intact.'}
                            </p>
                          </div>
                        ))}
                      </div>
                    );
                  })()}

                  {/* Verification Execution Controls */}
                  <div className="p-4 rounded-xl bg-slate-950 border border-emerald-500/30 space-y-4">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                      <div>
                        <h4 className="text-sm font-semibold text-slate-100 flex items-center space-x-2">
                          <Atom className="w-4 h-4 text-emerald-400" />
                          <span>Zaslon-QDS Teleportation Sampling Ratio</span>
                        </h4>
                        <p className="text-xs text-slate-400 mt-0.5">
                          Evaluates {(sampleRatio * 100).toFixed(0)}% (~{Math.round(4096 * sampleRatio)} circuits) of the 4,096
                          teleportation operations deterministically using session seed.
                        </p>
                      </div>
                      <div className="flex items-center space-x-3 font-mono text-xs">
                        <span className="px-2 py-1 rounded bg-slate-900 border border-slate-800 text-emerald-400 font-bold">
                          {(sampleRatio * 100).toFixed(0)}% Sample
                        </span>
                        <input
                          type="range"
                          min="0.02"
                          max="0.20"
                          step="0.01"
                          value={sampleRatio}
                          onChange={(e) => setSampleRatio(parseFloat(e.target.value))}
                          className="w-28 h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-emerald-500"
                        />
                      </div>
                    </div>

                    <button
                      onClick={handleExecuteVerification}
                      disabled={isVerifying || isAlreadyVerified}
                      className={`w-full py-3 rounded-xl text-xs font-bold uppercase tracking-wider font-mono flex items-center justify-center space-x-2 shadow-lg transition ${
                        isAlreadyVerified
                          ? selectedPackage?.status === 'VERIFIED' || detailedEvidence?.security_decision === 'VERIFIED'
                            ? 'bg-emerald-950/80 border border-emerald-500/50 text-emerald-400 cursor-not-allowed opacity-90'
                            : 'bg-red-950/80 border border-red-500/50 text-red-400 cursor-not-allowed opacity-90'
                          : 'bg-gradient-to-r from-emerald-600 to-cyan-600 hover:from-emerald-500 hover:to-cyan-500 text-white cursor-pointer'
                      }`}
                    >
                      {isVerifying ? (
                        <>
                          <RefreshCw className="w-4 h-4 animate-spin" />
                          <span>Executing 15-Check Zaslon-QDS Verification...</span>
                        </>
                      ) : isAlreadyVerified ? (
                        <>
                          {selectedPackage?.status === 'VERIFIED' || detailedEvidence?.security_decision === 'VERIFIED' ? (
                            <>
                              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                              <span>VERIFICATION COMPLETE: VERIFIED &amp; ACCEPTED (Stored)</span>
                            </>
                          ) : (
                            <>
                              <XCircle className="w-4 h-4 text-red-400" />
                              <span>VERIFICATION COMPLETE: REJECTED (Stored)</span>
                            </>
                          )}
                        </>
                      ) : (
                        <>
                          <ShieldCheck className="w-4 h-4" />
                          <span>VERIFY IN-FLIGHT TRANSMISSION (15 CHECKS)</span>
                        </>
                      )}
                    </button>
                  </div>

                  {/* Explainable Verification Result View */}
                  {detailedEvidence && renderEvidence(detailedEvidence, handleDownloadCertificate)}
                </div>
              ) : (
                <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-12 text-center space-y-4">
                  <Inbox className="w-12 h-12 text-slate-600 mx-auto" />
                  <h3 className="text-base font-bold text-slate-200">No Package Selected</h3>
                  <p className="text-xs text-slate-400 max-w-md mx-auto">
                    Select an incoming package from Bob's secure inbox on the left to inspect its manifest and execute the
                    11-step Zaslon-QDS verification suite.
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab 2: Manual Dual-File Upload Verification */}
        {activeTab === 'manual' && (
          <div className="space-y-6">
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-6 shadow-xl">
              <div>
                <h3 className="text-lg font-bold text-white font-mono flex items-center gap-2">
                  <Upload className="w-5 h-5 text-cyan-400" />
                  Offline / Manual Dual-Artifact Verification
                </h3>
                <p className="text-xs text-slate-400 mt-1">
                  Upload an offline document alongside its companion &lt;filename&gt;.qds.json cryptographic signature bundle.
                  The Zaslon-QDS engine will execute byte-level SHA-512 recomputation, token validation, and quantum teleportation Fisher exact tests.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Artifact 1: Document File */}
                <div
                  onClick={() => manualFileInputRef.current?.click()}
                  className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition ${
                    manualDocFile ? 'border-cyan-500 bg-cyan-950/20' : 'border-slate-700 hover:border-cyan-500/50 bg-slate-950'
                  }`}
                >
                  <input
                    ref={manualFileInputRef}
                    type="file"
                    onChange={(e) => e.target.files?.[0] && setManualDocFile(e.target.files[0])}
                    className="hidden"
                  />
                  <div className="flex flex-col items-center gap-2">
                    <FileCode className={`w-8 h-8 ${manualDocFile ? 'text-cyan-400' : 'text-slate-500'}`} />
                    <div className="text-sm font-bold font-mono text-slate-200">
                      {manualDocFile ? manualDocFile.name : '1. Select Signed Document File'}
                    </div>
                    <div className="text-xs text-slate-500 font-mono">
                      {manualDocFile ? `${(manualDocFile.size / 1024).toFixed(1)} KB` : 'PDF, DOCX, TXT, JSON, BIN'}
                    </div>
                  </div>
                </div>

                {/* Artifact 2: .qds.json package */}
                <div
                  onClick={() => manualQdsInputRef.current?.click()}
                  className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition ${
                    manualQdsFile ? 'border-purple-500 bg-purple-950/20' : 'border-slate-700 hover:border-purple-500/50 bg-slate-950'
                  }`}
                >
                  <input
                    ref={manualQdsInputRef}
                    type="file"
                    accept=".json"
                    onChange={(e) => e.target.files?.[0] && setManualQdsFile(e.target.files[0])}
                    className="hidden"
                  />
                  <div className="flex flex-col items-center gap-2">
                    <FileCheck className={`w-8 h-8 ${manualQdsFile ? 'text-purple-400' : 'text-slate-500'}`} />
                    <div className="text-sm font-bold font-mono text-slate-200">
                      {manualQdsFile ? manualQdsFile.name : '2. Select Companion <filename>.qds.json'}
                    </div>
                    <div className="text-xs text-slate-500 font-mono">
                      {manualQdsFile ? `${(manualQdsFile.size / 1024).toFixed(1)} KB` : 'Standard QDS JSON Bundle'}
                    </div>
                  </div>
                </div>
              </div>

              <button
                type="button"
                onClick={handleManualUploadVerify}
                disabled={isVerifying || !manualDocFile || !manualQdsFile}
                className="w-full py-3 rounded-xl bg-gradient-to-r from-cyan-600 to-emerald-600 hover:from-cyan-500 hover:to-emerald-500 text-white text-xs font-bold uppercase tracking-wider font-mono flex items-center justify-center space-x-2 shadow-lg transition disabled:opacity-40"
              >
                {isVerifying ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Executing 15-Check Verification on Artifacts...</span>
                  </>
                ) : (
                  <>
                    <ShieldCheck className="w-4 h-4" />
                    <span>VERIFY UPLOADED CRYPTOGRAPHIC ARTIFACTS (15 CHECKS)</span>
                  </>
                )}
              </button>

              {detailedEvidence && renderEvidence(detailedEvidence, handleDownloadCertificate)}
            </div>
          </div>
        )}

        {/* Tab 3: Audit Ledger */}
        {activeTab === 'history' && (
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-xl">
            <h2 className="text-base font-semibold text-slate-100 flex items-center space-x-2">
              <Clock className="w-4 h-4 text-emerald-400" />
              <span>Historical Zaslon-QDS Verifications</span>
            </h2>

            {historyList.length === 0 ? (
              <p className="text-xs text-slate-400 py-6 text-center font-mono">No verification records found in database.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs font-mono text-left">
                  <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
                    <tr>
                      <th className="p-3">Verification ID</th>
                      <th className="p-3">Session</th>
                      <th className="p-3">Security Decision</th>
                      <th className="p-3">Mismatch Ratio</th>
                      <th className="p-3">Fisher p-value</th>
                      <th className="p-3">Threat Flag</th>
                      <th className="p-3">Certificate</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {historyList.map((item) => (
                      <tr key={item.id} className="hover:bg-slate-950/40">
                        <td className="p-3 text-cyan-400 font-semibold">{item.id.slice(0, 8)}...</td>
                        <td className="p-3 text-slate-400">{item.session_id.slice(0, 8)}...</td>
                        <td className="p-3">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${
                              item.security_decision === 'VERIFIED'
                                ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                                : 'bg-red-500/20 text-red-300 border-red-500/30'
                            }`}
                          >
                            {item.security_decision}
                          </span>
                        </td>
                        <td className="p-3 text-slate-300">{((item.mismatch_ratio || 0) * 100).toFixed(2)}%</td>
                        <td className="p-3 text-slate-300">{item.fisher_p_value?.toFixed(6) ?? '1.000000'}</td>
                        <td className="p-3">
                          {item.attack_detected ? (
                            <span className="text-red-400 font-bold">{item.attack_category}</span>
                          ) : (
                            <span className="text-emerald-400">Authentic</span>
                          )}
                        </td>
                        <td className="p-3">
                          <button
                            onClick={() => handleDownloadCertificate(item.id)}
                            className="px-2 py-1 rounded bg-slate-950 hover:bg-slate-800 border border-slate-700 text-cyan-300 text-[10px] flex items-center gap-1"
                          >
                            <Award className="w-3 h-3" />
                            <span>.cert.json</span>
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Tab 4: Security Alerts & Intrusion Detection */}
        {activeTab === 'alerts' && (
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-xl">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold text-slate-100 flex items-center space-x-2">
                <ShieldAlert className="w-4 h-4 text-amber-400" />
                <span>Security Intrusion &amp; Access Violation Alerts</span>
              </h2>
              <span className="text-xs font-mono text-slate-400">
                Total Events: <span className="text-amber-400 font-bold">{securityEvents.length}</span>
              </span>
            </div>
            <p className="text-xs text-slate-400 font-mono">
              Live audit stream of unauthorized probe attempts and policy violations detected across the Zaslon-QDS verification boundaries.
            </p>

            {securityEvents.length === 0 ? (
              <p className="text-xs text-slate-400 py-8 text-center font-mono">
                No intrusion events recorded. All network verification endpoints operating within policy boundaries.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs font-mono text-left">
                  <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
                    <tr>
                      <th className="p-3">Event ID</th>
                      <th className="p-3">Timestamp</th>
                      <th className="p-3">Actor</th>
                      <th className="p-3">Violation Type</th>
                      <th className="p-3">Severity</th>
                      <th className="p-3">Resource Target</th>
                      <th className="p-3">Details</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {securityEvents.map((evt) => (
                      <tr key={evt.id} className="hover:bg-slate-950/40">
                        <td className="p-3 text-cyan-400 font-semibold">{evt.id.slice(0, 8)}...</td>
                        <td className="p-3 text-slate-400">
                          {evt.created_at ? new Date(evt.created_at).toLocaleTimeString() : 'N/A'}
                        </td>
                        <td className="p-3 text-slate-300 font-bold">{evt.actor}</td>
                        <td className="p-3">
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-amber-500/20 text-amber-300 border border-amber-500/30">
                            {evt.event_type}
                          </span>
                        </td>
                        <td className="p-3">
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-red-500/20 text-red-300 border border-red-500/30">
                            {evt.severity}
                          </span>
                        </td>
                        <td className="p-3 text-slate-400 truncate max-w-[180px]">{evt.resource}</td>
                        <td className="p-3 text-slate-300 max-w-[220px] truncate" title={JSON.stringify(evt.details)}>
                          {evt.details?.mechanism || evt.details?.reason || JSON.stringify(evt.details)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
};

// Helper: Renders 11-step stepper, decision banner, 5 barriers, Fisher matrix, and certificate download
function renderEvidence(evidence: VerificationEvidence, onDownloadCert: (id: string) => void) {
  const isVerified = evidence.security_decision === 'VERIFIED';

  return (
    <div className="space-y-6 pt-4 border-t border-slate-800">
      {/* 1. Security Decision Banner */}
      <div
        className={`p-5 rounded-2xl border flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-lg ${
          isVerified
            ? 'bg-emerald-950/60 border-emerald-500/60 text-emerald-100'
            : 'bg-red-950/60 border-red-500/60 text-red-100'
        }`}
      >
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            {isVerified ? (
              <CheckCircle2 className="w-6 h-6 text-emerald-400" />
            ) : (
              <XCircle className="w-6 h-6 text-red-400" />
            )}
            <span className="text-xl font-bold font-mono tracking-wide">
              VERDICT: {evidence.security_decision}
            </span>
          </div>
          <p className="text-xs text-slate-300 max-w-xl">{evidence.decision_reason}</p>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => onDownloadCert(evidence.verification_id)}
            className="px-4 py-2 rounded-xl bg-slate-950 hover:bg-slate-800 border border-emerald-400/50 text-emerald-300 text-xs font-mono font-bold flex items-center gap-2 shadow-lg transition"
          >
            <Award className="w-4 h-4 text-emerald-400" />
            <span>Download Certificate (.cert.json)</span>
          </button>
        </div>
      </div>

      {/* 2. 15-Check Verification Progression Stepper */}
      <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3 font-mono">
        <h4 className="text-xs font-bold uppercase tracking-wider text-cyan-400 flex items-center gap-2">
          <Layers className="w-4 h-4" />
          <span>15-Check Zaslon-QDS Verification Protocol Progression</span>
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2 pt-1 text-[11px]">
          {VERIFICATION_STEPS.map((st) => {
            return (
              <div
                key={st.step}
                className="p-2 rounded-lg bg-slate-900/60 border border-slate-800/80 flex items-start gap-2"
              >
                <div className="w-4 h-4 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 flex items-center justify-center text-[9px] font-bold flex-shrink-0 mt-0.5">
                  {st.step}
                </div>
                <div>
                  <div className="font-semibold text-slate-200">{st.name}</div>
                  <div className="text-[10px] text-slate-500">{st.desc}</div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 3. 5-Layer Threat Defense Barrier Checklist */}
      <div className="space-y-3 font-mono">
        <h4 className="text-sm font-semibold text-slate-200 flex items-center space-x-2">
          <ShieldCheck className="w-4 h-4 text-cyan-400" />
          <span>5-Layer Threat Defense Barrier Checklist</span>
        </h4>

        <div className="space-y-2">
          {evidence.defense_barriers.map((b, idx) => (
            <div
              key={idx}
              className={`p-3 rounded-xl border flex items-center justify-between gap-3 text-xs font-mono ${
                b.status === 'PASSED'
                  ? 'bg-slate-950/80 border-slate-800 text-slate-300'
                  : 'bg-red-950/40 border-red-500/50 text-red-200'
              }`}
            >
              <div className="flex items-center space-x-3">
                {b.status === 'PASSED' ? (
                  <Check className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                ) : (
                  <XCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
                )}
                <div>
                  <span className="font-bold text-slate-100">{b.barrier_name}</span>
                  <div className="text-[11px] text-slate-400">{b.detail}</div>
                </div>
              </div>
              <span
                className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${
                  b.status === 'PASSED'
                    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                    : 'bg-red-500/20 text-red-400 border-red-500/40'
                }`}
              >
                {b.status}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* 4. Quantum Statistical Evidence Matrix (Fisher Hypergeometric Test) */}
      <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-4">
        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
          Quantum Statistical Verification Receipt (Fisher's Exact Test)
        </h4>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
          <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
            <span className="text-slate-500 text-[10px] block">SAMPLE SIZE (N)</span>
            <span className="text-slate-200 font-bold text-sm">
              {evidence.statistical_evidence.sample_size}
            </span>
          </div>
          <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
            <span className="text-slate-500 text-[10px] block">MATCHES / MISMATCHES</span>
            <span className="text-slate-200 font-bold text-sm">
              {evidence.statistical_evidence.match_count} /{' '}
              <span
                className={
                  evidence.statistical_evidence.mismatch_count > 0 ? 'text-red-400' : 'text-emerald-400'
                }
              >
                {evidence.statistical_evidence.mismatch_count}
              </span>
            </span>
          </div>
          <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
            <span className="text-slate-500 text-[10px] block">OBSERVED MISMATCH RATIO</span>
            <span
              className={`font-bold text-sm ${
                evidence.statistical_evidence.mismatch_ratio > 0.03 ? 'text-red-400' : 'text-emerald-400'
              }`}
            >
              {evidence.statistical_evidence.mismatch_ratio_percent}
            </span>
            <span className="text-[10px] text-slate-500 block">
              Threshold: {evidence.statistical_evidence.threshold_ratio_percent}
            </span>
          </div>
          <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
            <span className="text-slate-500 text-[10px] block">FISHER EXACT P-VALUE</span>
            <span
              className={`font-bold text-sm ${
                (evidence.statistical_evidence.fisher_p_value ?? 0) >= 0.01 ? 'text-emerald-400' : 'text-red-400'
              }`}
            >
              {evidence.statistical_evidence.fisher_p_value != null
                ? evidence.statistical_evidence.fisher_p_value.toFixed(6)
                : '1.000000'}
            </span>
            <span className="text-[10px] text-slate-500 block">Alpha: 0.01</span>
          </div>
        </div>

        {/* 2x2 Contingency Table */}
        {evidence.statistical_evidence.contingency_table && (
          <div className="pt-2">
            <span className="text-[11px] font-mono text-slate-400 block mb-1.5">
              Contingency Matrix (Observed Teleportation vs Channel Baseline):
            </span>
            <div className="grid grid-cols-3 gap-1 max-w-md text-[11px] font-mono text-center">
              <div className="p-1.5 bg-slate-900 font-semibold text-slate-400 rounded">Category</div>
              <div className="p-1.5 bg-slate-900 font-semibold text-slate-400 rounded">Matches</div>
              <div className="p-1.5 bg-slate-900 font-semibold text-slate-400 rounded">Mismatches</div>

              <div className="p-1.5 bg-slate-950 text-slate-300 font-medium">Observed Sample</div>
              <div className="p-1.5 bg-slate-950 text-emerald-400 font-bold">
                {evidence.statistical_evidence.contingency_table[0]?.[0] ?? 0}
              </div>
              <div className="p-1.5 bg-slate-950 text-red-400 font-bold">
                {evidence.statistical_evidence.contingency_table[0]?.[1] ?? 0}
              </div>

              <div className="p-1.5 bg-slate-950 text-slate-300 font-medium">Baseline Channel</div>
              <div className="p-1.5 bg-slate-950 text-emerald-400 font-bold">
                {evidence.statistical_evidence.contingency_table[1]?.[0] ?? 0}
              </div>
              <div className="p-1.5 bg-slate-950 text-red-400 font-bold">
                {evidence.statistical_evidence.contingency_table[1]?.[1] ?? 0}
              </div>
            </div>
          </div>
        )}

        {/* Token Consumption Guarantee */}
        <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 text-xs text-slate-400 flex items-center space-x-2 font-mono">
          <Lock className="w-4 h-4 text-amber-400 flex-shrink-0" />
          <span>
            Anti-Replay Guarantee: Single-use token has been recorded as CONSUMED in database. Subsequent attempts will fail at Barrier 3.
          </span>
        </div>
      </div>
    </div>
  );
}
