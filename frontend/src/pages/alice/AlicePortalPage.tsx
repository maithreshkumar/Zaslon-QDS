import React, { useState, useEffect, useRef } from 'react';
import {
  Send,
  Atom,
  CheckCircle2,
  RefreshCw,
  FileText,
  Clock,
  Upload,
  Download,
  FileCheck,
  FileCode,
  Layers,
  AlertCircle
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { RoleNavbar } from '../../components/layout/RoleNavbar';
import { ProtocolFlowBar } from '../../components/protocol/ProtocolFlowBar';
import { CircuitDiagram } from '../../components/circuit/CircuitDiagram';
import { TransmissionPackage } from '../../types/auth';

export const AlicePortalPage: React.FC = () => {
  const { token } = useAuth();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [activeView, setActiveView] = useState<'create' | 'history'>('create');
  const [inputMode, setInputMode] = useState<'file' | 'directive'>('file');

  // Form inputs
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [documentTitle, setDocumentTitle] = useState('CRITICAL INFRASTRUCTURE DEFENSE DIRECTIVE #26141');
  const [directiveText, setDirectiveText] = useState(
    'MANDATE 26141: IMMEDIATE ACTIVATION OF QUANTUM-SECURED TELEPORTATION DIGITAL SIGNATURE CHANNELS ACROSS ALL REGIONAL GRID NODES.'
  );
  const [recipientId, setRecipientId] = useState('bob');
  const [recipientsList, setRecipientsList] = useState<{ id: string; name: string }[]>([]);

  // Signing lifecycle state
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentStep, setCurrentStep] = useState<'idle' | 'hashing' | 'signing' | 'signed' | 'dispatched'>('idle');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [fileSizeBytes, setFileSizeBytes] = useState<number | null>(null);
  const [sha512Digest, setSha512Digest] = useState<string | null>(null);
  const [quantumDurationMs, setQuantumDurationMs] = useState<number | null>(null);
  const [signatureToken, setSignatureToken] = useState<string | null>(null);
  const [dispatchedPackage, setDispatchedPackage] = useState<TransmissionPackage | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Packages history
  const [myPackages, setMyPackages] = useState<TransmissionPackage[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  // Format bytes helper
  const formatBytes = (bytes?: number) => {
    if (!bytes && bytes !== 0) return '0 B';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  // Fetch recipients
  useEffect(() => {
    const fetchRecipients = async () => {
      try {
        const res = await fetch('/api/v1/alice/recipients', {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          setRecipientsList(data);
          if (data.length > 0) setRecipientId(data[0].id);
        }
      } catch (err) {
        console.error('Error fetching recipients', err);
      }
    };
    if (token) fetchRecipients();
  }, [token]);

  // Fetch packages history
  const fetchMyPackages = async () => {
    setIsLoadingHistory(true);
    try {
      const res = await fetch('/api/v1/alice/packages', {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setMyPackages(data);
      }
    } catch (err) {
      console.error('Error fetching packages', err);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  useEffect(() => {
    if (token && activeView === 'history') {
      fetchMyPackages();
    }
  }, [token, activeView]);

  // Handle File Selection
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (file.size > 50 * 1024 * 1024) {
        setError('File size exceeds maximum allowable limit of 50 MB.');
        return;
      }
      setSelectedFile(file);
      setDocumentTitle(file.name.replace(/\.[^/.]+$/, ''));
      setError(null);
    }
  };

  // Execute full signing: Upload & Hash -> 4096 CUDA-Q Circuits -> Public Declaration
  const handleCreateQuantumSignature = async () => {
    if (inputMode === 'file' && !selectedFile) {
      setError('Please select a file to sign.');
      return;
    }
    if (inputMode === 'directive' && !directiveText.trim()) {
      setError('Please enter directive plaintext to sign.');
      return;
    }

    setIsProcessing(true);
    setError(null);
    setCurrentStep('hashing');

    try {
      // 1. Upload Document / Plaintext & Compute Canonical SHA-512
      const formData = new FormData();
      formData.append('document_title', documentTitle || 'Document_QDS_Signed');
      formData.append('recipient_id', recipientId);

      if (inputMode === 'file' && selectedFile) {
        formData.append('file', selectedFile);
      } else {
        formData.append('directive_text', directiveText);
      }

      const uploadRes = await fetch('/api/v1/alice/upload', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`
        },
        body: formData
      });

      if (!uploadRes.ok) {
        const err = await uploadRes.json();
        throw new Error(err.detail || 'Failed to process and hash document');
      }

      const uploadData = await uploadRes.json();
      setSessionId(uploadData.session_id);
      setFileName(uploadData.file_name);
      setFileSizeBytes(uploadData.file_size_bytes);
      setSha512Digest(uploadData.sha512_digest);

      // 2. Launch 4,096 Teleportation circuits on NVIDIA CUDA-Q
      setCurrentStep('signing');
      const signRes = await fetch(`/api/v1/alice/sessions/${uploadData.session_id}/sign`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      });

      if (!signRes.ok) {
        const err = await signRes.json();
        throw new Error(err.detail || 'Quantum signature generation failed on CUDA-Q');
      }

      const signData = await signRes.json();
      setQuantumDurationMs(signData.duration_ms);
      setSignatureToken(signData.signature_token);
      setCurrentStep('signed');
    } catch (err: any) {
      setError(err.message || 'Signature workflow failed');
      setCurrentStep('idle');
    } finally {
      setIsProcessing(false);
    }
  };

  // Dispatch Package (Enter IN_TRANSIT over Classical & Quantum Channels)
  const handleDispatchToBob = async () => {
    if (!sessionId) return;
    setIsProcessing(true);
    setError(null);

    try {
      const res = await fetch(`/api/v1/alice/packages/${sessionId}/dispatch`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Dispatch failed');
      }

      const pkgData: TransmissionPackage = await res.json();
      setDispatchedPackage(pkgData);
      setCurrentStep('dispatched');
    } catch (err: any) {
      setError(err.message || 'Failed to dispatch package into transmission channel');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDownloadQdsJson = async (targetSessionId: string, name?: string) => {
    try {
      const res = await fetch(`/api/v1/alice/packages/${targetSessionId}/qds-json`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!res.ok) throw new Error('Failed to download .qds.json package');
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${name || 'document'}.qds.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (err: any) {
      setError(err.message || 'Error downloading .qds.json package');
    }
  };

  const handleDownloadFile = async (targetSessionId: string, name?: string) => {
    try {
      const res = await fetch(`/api/v1/alice/files/${targetSessionId}/download`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!res.ok) throw new Error('Failed to download document');
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = name || 'signed_document';
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (err: any) {
      setError(err.message || 'Error downloading original file');
    }
  };

  const handleResetForNewSignature = () => {
    setCurrentStep('idle');
    setSessionId(null);
    setSelectedFile(null);
    setFileName(null);
    setFileSizeBytes(null);
    setSha512Digest(null);
    setQuantumDurationMs(null);
    setSignatureToken(null);
    setDispatchedPackage(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <div className="min-h-screen bg-zaslon-950 text-slate-100 flex flex-col">
      <RoleNavbar />

      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full">
        <ProtocolFlowBar currentRole="ALICE" />

        {/* Portal Header */}
        <div className="flex flex-wrap items-center justify-between gap-4 mb-8">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-cyan-400"></span>
              <span className="text-xs font-mono tracking-widest text-cyan-400 uppercase font-semibold">
                Alice Signer Portal
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold text-slate-100 mt-1 font-mono">
              Quantum Digital Signature Studio
            </h1>
            <p className="text-xs text-slate-400 mt-1">
              File-based 3-qubit quantum teleportation signatures on NVIDIA CUDA-Q with SHA-512 binding and dual-channel dispatch.
            </p>
          </div>

          <div className="flex items-center bg-zaslon-900 border border-zaslon-800 rounded-lg p-1 text-xs font-mono">
            <button
              onClick={() => setActiveView('create')}
              className={`px-3 py-1.5 rounded transition-colors ${
                activeView === 'create' ? 'bg-cyan-500/20 text-cyan-300 font-bold' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Sign New Document
            </button>
            <button
              onClick={() => setActiveView('history')}
              className={`px-3 py-1.5 rounded transition-colors ${
                activeView === 'history' ? 'bg-cyan-500/20 text-cyan-300 font-bold' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Sent Ledger ({myPackages.length})
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-6 p-4 rounded-xl bg-red-950/40 border border-red-500/40 text-red-300 text-xs font-mono flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0 text-red-400" />
            <span>{error}</span>
          </div>
        )}

        {/* View 1: Create Signature Flow */}
        {activeView === 'create' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
            {/* Left: Configuration & Actions */}
            <div className="lg:col-span-6 space-y-6">
              <div className="bg-zaslon-900/70 border border-zaslon-800 rounded-xl p-6 backdrop-blur-sm shadow-lg">
                <h3 className="text-sm font-bold font-mono text-slate-200 uppercase tracking-wider mb-4 flex items-center gap-2">
                  <FileText className="w-4 h-4 text-cyan-400" />
                  1. Document &amp; Target Recipient Selection
                </h3>

                {/* Input Mode Selector */}
                <div className="flex items-center gap-2 mb-5 p-1 bg-zaslon-950 rounded-lg border border-zaslon-800 text-xs font-mono">
                  <button
                    type="button"
                    onClick={() => setInputMode('file')}
                    disabled={currentStep !== 'idle'}
                    className={`flex-1 py-1.5 px-3 rounded flex items-center justify-center gap-2 transition-colors ${
                      inputMode === 'file'
                        ? 'bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/40'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <Upload className="w-3.5 h-3.5" />
                    <span>Upload Binary / Document File</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setInputMode('directive')}
                    disabled={currentStep !== 'idle'}
                    className={`flex-1 py-1.5 px-3 rounded flex items-center justify-center gap-2 transition-colors ${
                      inputMode === 'directive'
                        ? 'bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/40'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <FileCode className="w-3.5 h-3.5" />
                    <span>Type Plaintext Directive</span>
                  </button>
                </div>

                <div className="space-y-4">
                  {/* File Upload Mode */}
                  {inputMode === 'file' && (
                    <div>
                      <label className="block text-xs font-mono text-slate-400 uppercase mb-2">
                        Upload Document to Sign (PDF, TXT, DOCX, JSON, BIN)
                      </label>
                      <div
                        onClick={() => currentStep === 'idle' && fileInputRef.current?.click()}
                        className={`border-2 border-dashed rounded-xl p-6 text-center transition-all cursor-pointer ${
                          selectedFile
                            ? 'border-cyan-500/60 bg-cyan-950/20'
                            : 'border-zaslon-700 hover:border-cyan-500/50 bg-zaslon-950/50'
                        } ${currentStep !== 'idle' ? 'opacity-60 cursor-not-allowed' : ''}`}
                      >
                        <input
                          ref={fileInputRef}
                          type="file"
                          onChange={handleFileChange}
                          disabled={currentStep !== 'idle'}
                          className="hidden"
                        />
                        {selectedFile ? (
                          <div className="flex flex-col items-center gap-2">
                            <FileCheck className="w-8 h-8 text-cyan-400" />
                            <div className="text-sm font-bold font-mono text-slate-200">{selectedFile.name}</div>
                            <div className="text-xs font-mono text-cyan-400">
                              {formatBytes(selectedFile.size)} • {selectedFile.type || 'application/octet-stream'}
                            </div>
                            {currentStep === 'idle' && (
                              <div className="text-[11px] text-slate-400 mt-1 hover:text-cyan-300 underline">
                                Click to replace file
                              </div>
                            )}
                          </div>
                        ) : (
                          <div className="flex flex-col items-center gap-2">
                            <Upload className="w-8 h-8 text-slate-500" />
                            <div className="text-sm font-bold font-mono text-slate-300">
                              Drag &amp; Drop or Click to Browse File
                            </div>
                            <div className="text-xs text-slate-500 font-mono">
                              Arbitrary binary formats supported up to 50 MB
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Document Title */}
                  <div>
                    <label className="block text-xs font-mono text-slate-400 uppercase mb-1">
                      Document Title / Subject
                    </label>
                    <input
                      type="text"
                      value={documentTitle}
                      onChange={(e) => setDocumentTitle(e.target.value)}
                      disabled={currentStep !== 'idle'}
                      className="w-full bg-zaslon-950 border border-zaslon-700 rounded-lg px-3 py-2 text-sm font-mono text-slate-100 focus:outline-none focus:border-cyan-500 disabled:opacity-60"
                    />
                  </div>

                  {/* Plaintext Directive Mode */}
                  {inputMode === 'directive' && (
                    <div>
                      <label className="block text-xs font-mono text-slate-400 uppercase mb-1">
                        Plaintext Directive Content
                      </label>
                      <textarea
                        rows={4}
                        value={directiveText}
                        onChange={(e) => setDirectiveText(e.target.value)}
                        disabled={currentStep !== 'idle'}
                        className="w-full bg-zaslon-950 border border-zaslon-700 rounded-lg px-3 py-2 text-sm font-mono text-slate-100 focus:outline-none focus:border-cyan-500 disabled:opacity-60"
                      />
                    </div>
                  )}

                  {/* Verifier Recipient */}
                  <div>
                    <label className="block text-xs font-mono text-slate-400 uppercase mb-1">
                      Designated Verifier (Bob Node)
                    </label>
                    <select
                      value={recipientId}
                      onChange={(e) => setRecipientId(e.target.value)}
                      disabled={currentStep !== 'idle'}
                      className="w-full bg-zaslon-950 border border-zaslon-700 rounded-lg px-3 py-2 text-sm font-mono text-slate-100 focus:outline-none focus:border-cyan-500 disabled:opacity-60"
                    >
                      {recipientsList.map((r) => (
                        <option key={r.id} value={r.id}>
                          {r.name} ({r.id})
                        </option>
                      ))}
                      <option value="bob">Bob (Branch Verifier)</option>
                    </select>
                  </div>

                  {/* Action Button: Sign */}
                  {currentStep === 'idle' && (
                    <button
                      onClick={handleCreateQuantumSignature}
                      disabled={isProcessing || (inputMode === 'file' && !selectedFile)}
                      className="w-full py-3.5 px-4 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-mono text-sm font-bold transition-all shadow-lg shadow-cyan-500/20 flex items-center justify-center gap-2 disabled:opacity-50 mt-4"
                    >
                      <Atom className="w-4 h-4 animate-spin-slow" />
                      <span>SIGN WITH 3-QUBIT TELEPORTATION (4,096 CIRCUITS)</span>
                    </button>
                  )}
                </div>
              </div>

              {/* Step 2: Signature Prepared & Ready to Send */}
              {(currentStep === 'signed' || currentStep === 'dispatched') && (
                <div className="bg-zaslon-900/70 border border-cyan-500/40 rounded-xl p-6 backdrop-blur-sm shadow-xl space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-xs font-mono text-cyan-400 uppercase font-semibold">
                      <CheckCircle2 className="w-4 h-4 text-cyan-400" />
                      <span>2. Signature Created &amp; Manifest Sealed</span>
                    </div>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
                      AUTHENTIC QDS
                    </span>
                  </div>

                  <h3 className="text-base font-bold text-slate-100 font-mono">
                    Ready to Dispatch to {recipientId}
                  </h3>

                  <div className="p-3 rounded-lg bg-zaslon-950 border border-zaslon-800 space-y-2 text-xs font-mono">
                    <div className="flex justify-between items-center">
                      <span className="text-slate-500">Document Name:</span>
                      <span className="text-slate-200 font-semibold">{fileName || selectedFile?.name}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-slate-500">File Size:</span>
                      <span className="text-slate-300">{formatBytes(fileSizeBytes || selectedFile?.size)}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-slate-500">SHA-512 Digest:</span>
                      <span className="text-cyan-400 truncate max-w-[220px]" title={sha512Digest || ''}>
                        {sha512Digest}
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-slate-500">CUDA-Q Circuits:</span>
                      <span className="text-slate-300">4,096 operations (3 qubits each = 12,288 qubits)</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-slate-500">Quantum Execution Time:</span>
                      <span className="text-slate-300">{quantumDurationMs?.toFixed(1)} ms</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-slate-500">Public Token:</span>
                      <span className="text-emerald-400 truncate max-w-[220px]" title={signatureToken || ''}>
                        {signatureToken}
                      </span>
                    </div>
                  </div>

                  {/* Artifact Download Options */}
                  <div className="grid grid-cols-2 gap-3 pt-1">
                    <button
                      type="button"
                      onClick={() => sessionId && handleDownloadQdsJson(sessionId, fileName || 'document')}
                      className="py-2 px-3 rounded-lg bg-zaslon-950 hover:bg-zaslon-800 border border-zaslon-700 text-cyan-300 font-mono text-xs flex items-center justify-center gap-1.5 transition-colors"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>Download .qds.json</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => sessionId && handleDownloadFile(sessionId, fileName || 'document')}
                      className="py-2 px-3 rounded-lg bg-zaslon-950 hover:bg-zaslon-800 border border-zaslon-700 text-slate-300 font-mono text-xs flex items-center justify-center gap-1.5 transition-colors"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>Download File</span>
                    </button>
                  </div>

                  {currentStep === 'signed' ? (
                    <button
                      onClick={handleDispatchToBob}
                      disabled={isProcessing}
                      className="w-full py-3 px-4 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-mono text-sm font-bold transition-all shadow-lg shadow-emerald-500/20 flex items-center justify-center gap-2 mt-2"
                    >
                      <Send className="w-4 h-4" />
                      <span>DISPATCH TO BOB (TRANSMIT OVER DUAL CHANNELS)</span>
                    </button>
                  ) : (
                    <div className="space-y-3 pt-2">
                      <div className="p-4 rounded-lg bg-emerald-950/40 border border-emerald-500/40 text-emerald-300 text-xs font-mono space-y-1">
                        <div className="flex items-center gap-2 font-bold text-emerald-400">
                          <CheckCircle2 className="w-4 h-4" />
                          <span>PACKAGE TRANSMISSION DISPATCHED</span>
                        </div>
                        <div className="text-slate-300 text-[11px]">
                          Tracking No: <span className="text-cyan-400 font-semibold">{dispatchedPackage?.package_tracking_no}</span>
                        </div>
                        <div className="text-[10px] text-slate-400 mt-2 space-y-1">
                          <div>• <span className="text-slate-300">Classical Channel:</span> Document &amp; .qds.json transmitted via Application-Level Classical Transmission</div>
                          <div>• <span className="text-slate-300">Quantum Channel:</span> Teleportation bell-states routed via 25 km optical fiber</div>
                        </div>
                      </div>
                      <button
                        onClick={handleResetForNewSignature}
                        className="w-full py-2 px-4 rounded-lg border border-zaslon-700 bg-zaslon-800 hover:bg-zaslon-700 text-slate-300 font-mono text-xs transition-colors"
                      >
                        Sign Another Document
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Right: Quantum Teleportation Circuit & Live Diagnostics */}
            <div className="lg:col-span-6 space-y-6">
              <div className="bg-zaslon-900/70 border border-zaslon-800 rounded-xl p-6 backdrop-blur-sm shadow-lg">
                <h3 className="text-sm font-bold font-mono text-slate-200 uppercase tracking-wider mb-2 flex items-center gap-2">
                  <Atom className="w-4 h-4 text-cyan-400" />
                  3-Qubit Quantum Teleportation Circuit (CUDA-Q)
                </h3>
                <p className="text-xs text-slate-400 mb-4">
                  Genuine NVIDIA CUDA-Q execution: State preparation on Q0, Bell-pair creation on Q1-Q2, Bell-state measurement on Q0-Q1, and Pauli-feedforward corrections (X^m1 Z^m0) on Q2.
                </p>
                <div className="bg-zaslon-950 border border-zaslon-800 rounded-lg p-3">
                  <CircuitDiagram />
                </div>
              </div>

              {/* Progress Panel when Processing */}
              {isProcessing && (
                <div className="bg-zaslon-900/70 border border-cyan-500/40 rounded-xl p-6 backdrop-blur-sm shadow-xl">
                  <div className="flex items-center gap-3 text-cyan-400 font-mono text-xs mb-3">
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span className="font-bold uppercase tracking-wider">
                      {currentStep === 'hashing' && 'Streaming 64KB chunked SHA-512 byte digest...'}
                      {currentStep === 'signing' && 'Executing 4,096 Teleportation circuits on NVIDIA CUDA-Q...'}
                    </span>
                  </div>
                  <div className="w-full h-2 bg-zaslon-950 rounded-full overflow-hidden border border-zaslon-800">
                    <div className="h-full bg-cyan-400 animate-pulse w-3/4"></div>
                  </div>
                </div>
              )}

              {/* Network Simulation Architecture Card */}
              <div className="bg-zaslon-900/70 border border-zaslon-800 rounded-xl p-6 backdrop-blur-sm text-xs font-mono space-y-3">
                <div className="flex items-center gap-2 text-slate-300 font-bold uppercase tracking-wider">
                  <Layers className="w-4 h-4 text-cyan-400" />
                  <span>Dual-Channel Quantum Network Specification</span>
                </div>
                <div className="grid grid-cols-2 gap-3 text-[11px]">
                  <div className="p-2.5 rounded bg-zaslon-950 border border-zaslon-800">
                    <div className="text-slate-500 uppercase">Classical Link</div>
                    <div className="text-slate-200 font-semibold mt-0.5">Application-Level Classical Transmission</div>
                    <div className="text-[10px] text-slate-400 mt-1">Carries .qds.json manifest &amp; document bytes</div>
                  </div>
                  <div className="p-2.5 rounded bg-zaslon-950 border border-zaslon-800">
                    <div className="text-slate-500 uppercase">Quantum Fiber</div>
                    <div className="text-cyan-400 font-semibold mt-0.5">25.0 km Single-Mode</div>
                    <div className="text-[10px] text-slate-400 mt-1">0.2 dB/km loss, 122.5 µs latency, T2 decoherence</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* View 2: Dispatched Packages History */}
        {activeView === 'history' && (
          <div className="bg-zaslon-900/70 border border-zaslon-800 rounded-xl p-6 backdrop-blur-sm">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold font-mono text-slate-200 uppercase tracking-wider flex items-center gap-2">
                <Clock className="w-4 h-4 text-cyan-400" />
                Alice's Signed Packages Ledger
              </h3>
              <button
                onClick={fetchMyPackages}
                disabled={isLoadingHistory}
                className="text-xs font-mono text-slate-400 hover:text-cyan-400 flex items-center gap-1"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isLoadingHistory ? 'animate-spin' : ''}`} />
                <span>Refresh</span>
              </button>
            </div>

            {myPackages.length === 0 ? (
              <div className="py-12 text-center text-slate-500 font-mono text-xs">
                No dispatched packages recorded yet.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs font-mono">
                  <thead>
                    <tr className="border-b border-zaslon-800 text-slate-400">
                      <th className="py-3 px-3">Tracking No</th>
                      <th className="py-3 px-3">File / Title</th>
                      <th className="py-3 px-3">Recipient</th>
                      <th className="py-3 px-3">SHA-512 Digest</th>
                      <th className="py-3 px-3">Status</th>
                      <th className="py-3 px-3">Dispatched At</th>
                      <th className="py-3 px-3 text-right">Artifacts</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zaslon-800/60">
                    {myPackages.map((pkg) => (
                      <tr key={pkg.id} className="hover:bg-zaslon-800/30 transition-colors">
                        <td className="py-3 px-3 text-cyan-400 font-semibold">{pkg.package_tracking_no}</td>
                        <td className="py-3 px-3 text-slate-200">
                          {pkg.file_name || 'Plaintext Directive'}
                          {pkg.file_size_bytes ? (
                            <span className="text-[10px] text-slate-500 block">
                              {formatBytes(pkg.file_size_bytes)}
                            </span>
                          ) : null}
                        </td>
                        <td className="py-3 px-3 text-slate-300">{pkg.recipient_id}</td>
                        <td className="py-3 px-3 text-slate-400 truncate max-w-[140px]" title={pkg.committed_digest}>
                          {pkg.committed_digest}
                        </td>
                        <td className="py-3 px-3">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${
                              pkg.status === 'VERIFIED'
                                ? 'bg-emerald-950 text-emerald-400 border-emerald-800'
                                : pkg.status === 'REJECTED'
                                ? 'bg-red-950 text-red-400 border-red-800'
                                : pkg.status === 'IN_TRANSIT'
                                ? 'bg-cyan-950 text-cyan-400 border-cyan-800 animate-pulse'
                                : 'bg-zaslon-950 text-slate-400 border-zaslon-700'
                            }`}
                          >
                            {pkg.status}
                          </span>
                        </td>
                        <td className="py-3 px-3 text-slate-500">
                          {new Date(pkg.created_at).toLocaleTimeString()}
                        </td>
                        <td className="py-3 px-3 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={() => handleDownloadQdsJson(pkg.session_id, pkg.file_name)}
                              title="Download .qds.json package"
                              className="px-2 py-1 rounded bg-zaslon-950 hover:bg-zaslon-800 border border-zaslon-700 text-cyan-300 text-[10px] flex items-center gap-1"
                            >
                              <Download className="w-3 h-3" />
                              <span>.qds.json</span>
                            </button>
                            <button
                              onClick={() => handleDownloadFile(pkg.session_id, pkg.file_name)}
                              title="Download signed file"
                              className="px-2 py-1 rounded bg-zaslon-950 hover:bg-zaslon-800 border border-zaslon-700 text-slate-300 text-[10px] flex items-center gap-1"
                            >
                              <Download className="w-3 h-3" />
                              <span>File</span>
                            </button>
                          </div>
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
