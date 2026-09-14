import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { ArrowRight, Download, FileCheck2, FileKey2, Info, LockKeyhole, ShieldCheck, UploadCloud } from 'lucide-react';
import '../../design-system.css';

const API = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8101/api/v1';
const apiFetch = fetch;

type Health = {status:string;protocol_version:string;database:string;quantum:{available?:boolean;execution_target?:string;target?:string;gpu?:string|boolean}};

function Topbar({health}:{health:Health|null}) {
  const online=health?.status==='ok';
  return <header className="topbar">
    <div className="brand"><div className="brand-mark"><span className="brand-dot" /></div><div><div className="brand-name">ZASLON—QDS</div><div className="brand-sub">Quantum signature laboratory</div></div></div>
    <div className="system-status"><i /> {health==null?'CHECKING NODE':online?'RESEARCH NODE ONLINE':'NODE DEGRADED'}</div>
  </header>;
}

function downloadJson(data: unknown, filename: string) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'}));
  const anchor = window.document.createElement('a');
  anchor.href = url; anchor.download = filename; anchor.style.display = 'none';
  window.document.body.appendChild(anchor); anchor.click(); anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function downloadSignedArtifact(downloadPath: string, filename: string) {
  const apiOrigin = API.replace(/\/api\/v1\/?$/, '');
  const response = await apiFetch(`${apiOrigin}${downloadPath}`);
  if (!response.ok) throw new Error('The signed artifact could not be downloaded from the trusted session store');
  const url = URL.createObjectURL(await response.blob());
  const anchor = window.document.createElement('a');
  anchor.href = url; anchor.download = filename; anchor.style.display = 'none';
  window.document.body.appendChild(anchor); anchor.click(); anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

type CreationResult = {
  session: {id:string; document_name:string; created_at:string};
  signature: Record<string, unknown> & {signature_id:string; prepared_quantum_states:number;maximum_simultaneous_circuit_qubits:number;quantum_diagnostic:{status:string;z_basis:{correlation:number};x_basis:{correlation:number}};effective_channel_diagnostic:{status:string;z_basis:{correlation:number};x_basis:{correlation:number};state_metrics:{bell_state_fidelity:number|null}};quantum_status:{teleportation:{bell_pairs_consumed:number}}};
  encryption: Record<string, unknown> | null;
  quantum: {engine:string; target:string; maximum_circuit_width:number};
  baseline: {usable_measurements:number; mismatches:number; mean_teleportation_fidelity:number|null};
  artifact: {filename:string; media_type:string; download_url:string};
  performance: {signature_generation_latency_ms:number;teleportations_per_second:number|null;diagnostic_shots:number};
};

function ScientificSummary({result}:{result:CreationResult}) {
  const ideal=result.signature.quantum_diagnostic;
  const effective=result.signature.effective_channel_diagnostic;
  return <section className="card" style={{marginTop:20}}><div className="card-header"><div><div className="card-title">Scientific execution summary</div><div className="card-kicker">Source quality and effective distribution are separate</div></div><span className="status-pill good">EMPIRICAL</span></div><div className="card-body"><div className="metric-grid"><div className="metric"><div className="metric-label">Bell pairs consumed</div><div className="metric-value cyan">{result.signature.quantum_status.teleportation.bell_pairs_consumed}</div></div><div className="metric"><div className="metric-label">Max simultaneous qubits</div><div className="metric-value">{result.signature.maximum_simultaneous_circuit_qubits}</div></div><div className="metric"><div className="metric-label">Ideal source ZZ / XX</div><div className="metric-value" style={{fontSize:13}}>{ideal.z_basis.correlation.toFixed(3)} / {ideal.x_basis.correlation.toFixed(3)}</div></div><div className="metric"><div className="metric-label">Effective ZZ / XX</div><div className="metric-value" style={{fontSize:13}}>{effective.z_basis.correlation.toFixed(3)} / {effective.x_basis.correlation.toFixed(3)}</div></div><div className="metric"><div className="metric-label">Signing latency</div><div className="metric-value">{result.performance.signature_generation_latency_ms.toFixed(1)} ms</div></div><div className="metric"><div className="metric-label">Throughput</div><div className="metric-value">{result.performance.teleportations_per_second==null?'N/A':`${result.performance.teleportations_per_second.toFixed(0)} tps`}</div></div><div className="metric"><div className="metric-label">Ideal diagnostic</div><div className="metric-value" style={{fontSize:12}}>{ideal.status}</div></div><div className="metric"><div className="metric-label">Effective diagnostic</div><div className="metric-value" style={{fontSize:12}}>{effective.status}</div></div></div><div className="helper">Bell pairs are consumed sequentially; this count does not mean all qubits coexist. The maximum teleportation circuit width is three qubits. Diagnostics are empirical and do not prove information-theoretic QDS security.</div></div></section>;
}

function AliceApp() {
  const [document, setDocument] = useState<File | null>(null);
  const [verifier, setVerifier] = useState('Bob');
  const [encrypt, setEncrypt] = useState(true);
  const [passphrase, setPassphrase] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<CreationResult | null>(null);
  const [health,setHealth]=useState<Health|null>(null);
  useEffect(()=>{void apiFetch(`${API}/health`).then(response=>response.json()).then(setHealth).catch(()=>setHealth({status:'offline',protocol_version:'unknown',database:'unavailable',quantum:{available:false}}))},[]);
  const canSubmit = useMemo(() => Boolean(document && (!encrypt || passphrase.length >= 8)), [document, encrypt, passphrase]);

  async function createSession() {
    if (!document) return;
    setBusy(true); setError(''); setResult(null);
    const body = new FormData(); body.append('document', document); body.append('signer_id', 'Alice'); body.append('verifier_id', verifier);
    if (encrypt) body.append('encryption_passphrase', passphrase);
    try {
      const response = await apiFetch(`${API}/alice/sessions`, {method:'POST', body});
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? 'Session creation failed');
      setResult(payload);
      await downloadSignedArtifact(
        payload.artifact.download_url,
        payload.artifact.filename ?? `${document.name}.qds.json`,
      );
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Session creation failed'); }
    finally { setBusy(false); }
  }

  function reset() { setDocument(null); setPassphrase(''); setError(''); setResult(null); }

  return <div className="app-shell"><Topbar health={health}/><main className="page">
    <div className="page-heading"><div><div className="eyebrow">Alice / origin node</div><h1>Create a trusted quantum signature session.</h1><p className="lead">Bind a document to one-time QDS material, distribute verifier evidence to Bob, and optionally seal the payload with a separate AES-256-GCM confidentiality layer.</p></div><div className="page-index">NODE 01<br/>SIGNER</div></div>
    <div className="timeline"><div className="timeline-step"><span>01</span>Prepare document</div><div className="timeline-step"><span>02</span>Distribute states</div><div className="timeline-step"><span>03</span>Export artifacts</div></div>
    <div className="grid">
      <section className="card"><div className="card-header"><div><div className="card-title">Session composer</div><div className="card-kicker">SHA-512 • one-time resource</div></div><span className="step-badge">ALICE AUTHORITY</span></div><div className="card-body">
        <div className="field"><label className="label">Document</label><label className="dropzone"><input type="file" hidden onChange={event => setDocument(event.target.files?.[0] ?? null)} /><span className="dropzone-icon"><UploadCloud size={20}/></span><strong>{document?.name ?? 'Choose the document Alice will sign'}</strong><span>{document ? `${(document.size/1024).toFixed(1)} KB ready for SHA-512 binding` : 'PDF, text, image, archive, or any binary file'}</span></label></div>
        <div className="field"><label className="label">Verifier identity</label><input className="input" value={verifier} onChange={event=>setVerifier(event.target.value)} placeholder="Bob" /></div>
        <div className="field"><label className="label">Payload handling</label><div className="segmented"><button className={`segment ${!encrypt?'active':''}`} onClick={()=>setEncrypt(false)}>Signature only</button><button className={`segment ${encrypt?'active':''}`} onClick={()=>setEncrypt(true)}>Sign + encrypt</button></div></div>
        {encrypt && <div className="field"><label className="label">Encryption passphrase</label><input className="input mono" type="password" value={passphrase} onChange={event=>setPassphrase(event.target.value)} placeholder="At least 8 characters"/><div className="helper">Used locally by the API to derive an AES-256-GCM key with scrypt. The passphrase is never stored in the QDS artifact.</div></div>}
        <div className="notice"><Info size={17}/><div><strong>Scientific boundary.</strong> QDS authenticates origin and integrity. AES-GCM provides confidentiality. SHA-512 is a hash, not encryption.</div></div>
        {error && <div className="notice error" style={{marginTop:14}}>{error}</div>}
        <div className="button-row"><button className="btn btn-secondary" onClick={reset}>Reset</button><button className="btn btn-primary" disabled={!canSubmit || busy} onClick={createSession}>{busy?<><span className="spinner"/>Preparing 4,096 states…</>:<>Create secure session <ArrowRight size={15}/></>}</button></div>
      </div></section>
      <aside className="stack">
        <section className="card"><div className="card-header"><div><div className="card-title">Teleportation resource</div><div className="card-kicker">Maximum circuit width • 3 qubits</div></div><span className="status-pill good">READY</span></div><div className="quantum-viz"><div className="orbit one"/><div className="orbit two"/><div className="orbit three"/><div className="particle p1"/><div className="particle p2"/><div className="particle p3"/><div className="qubit-core">|ψ〉</div><div className="viz-caption"><span>ALICE q₀,q₁</span><span>BOB q₂</span></div></div></section>
        <section className="card"><div className="card-header"><div><div className="card-title">Protocol contract</div><div className="card-kicker">{health?.protocol_version??'Loading protocol version…'}</div></div><ShieldCheck size={18} color="var(--violet)"/></div><div className="card-body"><div className="metric-grid"><div className="metric"><div className="metric-label">Digest</div><div className="metric-value">SHA-512</div></div><div className="metric"><div className="metric-label">Prepared states</div><div className="metric-value cyan">4,096</div></div><div className="metric"><div className="metric-label">Evidence bases</div><div className="metric-value">X + Z</div></div><div className="metric"><div className="metric-label">Threshold</div><div className="metric-value">5%*</div></div></div><div className="helper">* Configured experimental parameter, not a proven security bound. Runtime: {health?.quantum.execution_target??health?.quantum.target??'not reported'}.</div></div></section>
      </aside>
    </div>
    {result && <section className="card" style={{marginTop:20}}><div className="result-hero"><span className="status-pill good">SESSION COMMITTED</span><div className="result-title good">Alice’s artifacts are ready.</div><div className="result-copy">{result.artifact.filename} downloaded automatically • Bob’s verifier evidence remains private in the trusted session store.</div></div><div className="card-body"><div className="metric-grid"><div className="metric"><div className="metric-label">Signature ID</div><div className="metric-value" style={{fontSize:12}}>{result.signature.signature_id}</div></div><div className="metric"><div className="metric-label">Quantum engine</div><div className="metric-value" style={{fontSize:13}}>{result.quantum.engine}</div></div><div className="metric"><div className="metric-label">Usable evidence</div><div className="metric-value cyan">{result.baseline.usable_measurements}</div></div><div className="metric"><div className="metric-label">Baseline errors</div><div className="metric-value">{result.baseline.mismatches}</div></div></div><div className="button-row"><button className="btn btn-secondary" onClick={()=>void downloadSignedArtifact(result.artifact.download_url, result.artifact.filename)}><FileCheck2 size={15}/> Download signature again</button>{result.encryption && <button className="btn btn-primary" onClick={()=>downloadJson(result.encryption, `${result.session.document_name}.zaslon.json`)}><LockKeyhole size={15}/> Download encrypted payload</button>}</div></div></section>}
    {result && <ScientificSummary result={result}/>} 
  </main></div>;
}

createRoot(document.getElementById('root')!).render(<React.StrictMode><AliceApp /></React.StrictMode>);
