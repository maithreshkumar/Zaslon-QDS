import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { CheckCircle2, Download, FileJson2, Fingerprint, KeyRound, LockOpen, SearchCheck, ShieldAlert, UploadCloud } from 'lucide-react';
import '../../design-system.css';

const API = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8102/api/v1';
const apiFetch = fetch;

type Health={status:string;protocol_version:string;quantum:{available?:boolean;execution_target?:string;target?:string}};

function Topbar({health}:{health:Health|null}) {
  return <header className="topbar"><div className="brand"><div className="brand-mark"><span className="brand-dot" /></div><div><div className="brand-name">ZASLON—QDS</div><div className="brand-sub">Quantum signature laboratory</div></div></div><div className="system-status"><i /> {health==null?'CHECKING VERIFIER':health.status==='ok'?'VERIFIER VAULT ONLINE':'VERIFIER DEGRADED'}</div></header>;
}

type BasisMetric={usable_measurements:number;mismatches:number;error_rate:number|null};
type VerifyResult = {status:string; reason:string; document_hash_match:boolean; usable_measurements:number; mismatches:number; mismatch_rate:number|null; threshold:number; threshold_source:string; replay_detected:boolean;failure_code:string|null;authenticated_verifier:string|null;basis_statistics:{Z:BasisMetric;X:BasisMetric;phase_sensitive_evidence:boolean}|null;performance:{verification_latency_ms:number}};

function FilePicker({title, file, onChange, accept}: {title:string; file:File|null; onChange:(file:File|null)=>void; accept?:string}) {
  return <label className="dropzone"><input hidden type="file" accept={accept} onChange={event=>onChange(event.target.files?.[0]??null)}/><span className="dropzone-icon"><UploadCloud size={20}/></span><strong>{file?.name ?? title}</strong><span>{file ? `${(file.size/1024).toFixed(1)} KB loaded` : 'Click to select an artifact'}</span></label>;
}

function BobApp() {
  const [mode, setMode] = useState<'verify'|'decrypt'>('verify');
  const [documentFile, setDocumentFile] = useState<File|null>(null);
  const [signatureFile, setSignatureFile] = useState<File|null>(null);
  const [encryptedFile, setEncryptedFile] = useState<File|null>(null);
  const [passphrase, setPassphrase] = useState('');
  const [result, setResult] = useState<VerifyResult|null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [health,setHealth]=useState<Health|null>(null);
  useEffect(()=>{void apiFetch(`${API}/health`).then(response=>response.json()).then(setHealth).catch(()=>setHealth({status:'offline',protocol_version:'unknown',quantum:{available:false}}))},[]);

  async function verify() {
    if (!documentFile || !signatureFile) return;
    setBusy(true); setError(''); setResult(null);
    const body = new FormData(); body.append('document', documentFile); body.append('signature', signatureFile);
    try { const response=await apiFetch(`${API}/bob/verify`,{method:'POST',body}); const payload=await response.json(); if(!response.ok) throw new Error(payload.detail??'Verification failed'); setResult(payload); }
    catch(reason){setError(reason instanceof Error?reason.message:'Verification failed');} finally{setBusy(false);}
  }

  async function decrypt() {
    if (!encryptedFile) return;
    setBusy(true); setError('');
    try {
      const encryptedPackage=JSON.parse(await encryptedFile.text());
      const response=await apiFetch(`${API}/bob/decrypt`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({encrypted_package:encryptedPackage,passphrase})});
      if(!response.ok){const payload=await response.json();throw new Error(payload.detail??'Decryption failed');}
      const blob=await response.blob(); const disposition=response.headers.get('Content-Disposition')??''; const match=/filename="([^"]+)"/.exec(disposition); const filename=match?.[1]??'decrypted.bin';
      const url=URL.createObjectURL(blob);const anchor=document.createElement('a');anchor.href=url;anchor.download=filename;anchor.click();URL.revokeObjectURL(url);
    } catch(reason){setError(reason instanceof Error?reason.message:'Decryption failed');} finally{setBusy(false);}
  }

  const good=result?.status==='VALID';
  return <div className="app-shell"><Topbar health={health}/><main className="page">
    <div className="page-heading"><div><div className="eyebrow">Bob / verifier node</div><h1>Open the payload. Prove who signed it.</h1><p className="lead">Bob keeps trusted measurement evidence private, validates the SHA-512 document binding, enforces one-time session use, and decrypts only when the separate confidentiality package authenticates correctly.</p></div><div className="page-index">NODE 03<br/>VERIFIER</div></div>
    <div className="grid"><section className="card"><div className="card-header"><div><div className="card-title">Verifier console</div><div className="card-kicker">Private evidence boundary</div></div><span className="step-badge">BOB AUTHORITY</span></div><div className="card-body">
      <div className="field"><div className="segmented"><button className={`segment ${mode==='verify'?'active':''}`} onClick={()=>{setMode('verify');setError('')}}><SearchCheck size={14} style={{verticalAlign:'middle',marginRight:7}}/>Verify signature</button><button className={`segment ${mode==='decrypt'?'active':''}`} onClick={()=>{setMode('decrypt');setError('')}}><LockOpen size={14} style={{verticalAlign:'middle',marginRight:7}}/>Decrypt payload</button></div></div>
      {mode==='verify'?<><div className="field"><label className="label">Original document</label><FilePicker title="Choose the document to verify" file={documentFile} onChange={setDocumentFile}/></div><div className="field"><label className="label">QDS signature artifact</label><FilePicker title="Choose the .qds.json artifact" file={signatureFile} onChange={setSignatureFile} accept="application/json,.json"/></div><div className="notice"><Fingerprint size={17}/><div>Only Bob’s verifier component can read the stored measurement outcomes. The uploaded signature cannot alter the trusted threshold or private evidence.</div></div><div className="button-row"><button className="btn btn-secondary" onClick={()=>{setDocumentFile(null);setSignatureFile(null);setResult(null);setError('')}}>Reset</button><button className="btn btn-primary" disabled={!documentFile||!signatureFile||busy} onClick={verify}>{busy?<><span className="spinner"/>Comparing evidence…</>:<><SearchCheck size={15}/>Verify once</>}</button></div></>:<><div className="field"><label className="label">Encrypted ZASLON package</label><FilePicker title="Choose the .zaslon.json package" file={encryptedFile} onChange={setEncryptedFile} accept="application/json,.json"/></div><div className="field"><label className="label">Shared passphrase</label><input type="password" className="input mono" value={passphrase} onChange={event=>setPassphrase(event.target.value)} placeholder="AES-GCM passphrase"/><div className="helper">Authentication failure is reported for either a wrong passphrase or a modified ciphertext; the API does not reveal which.</div></div><div className="button-row"><button className="btn btn-secondary" onClick={()=>{setEncryptedFile(null);setPassphrase('');setError('')}}>Reset</button><button className="btn btn-primary" disabled={!encryptedFile||passphrase.length<8||busy} onClick={decrypt}>{busy?<><span className="spinner"/>Authenticating…</>:<><Download size={15}/>Decrypt & download</>}</button></div></>}
      {error&&<div className="notice error" style={{marginTop:14}}><ShieldAlert size={17}/>{error}</div>}
    </div></section>
    <aside className="stack"><section className="card"><div className="card-header"><div><div className="card-title">Trust verdict</div><div className="card-kicker">Normal verifier path • {health?.protocol_version??'version unavailable'}</div></div>{result&&<span className={`status-pill ${good?'good':'bad'}`}>{result.status}</span>}</div>{!result?<div className="empty"><div><div className="empty-icon"><FileJson2 size={22}/></div><strong>No verification yet</strong><div className="helper">Load a document and its QDS artifact to inspect Bob’s trusted evidence.</div></div></div>:<><div className="result-hero"><div className={`result-title ${good?'good':'bad'}`}>{good?'SIGNATURE VALID':result.replay_detected?'REPLAY REJECTED':'SIGNATURE INVALID'}</div><div className="result-copy">{result.reason}</div></div><div className="card-body"><div className="metric-grid"><div className="metric"><div className="metric-label">Hash binding</div><div className={`metric-value ${result.document_hash_match?'cyan':'coral'}`}>{result.document_hash_match?'MATCH':'FAILED'}</div></div><div className="metric"><div className="metric-label">Usable evidence</div><div className="metric-value">{result.usable_measurements}</div></div><div className="metric"><div className="metric-label">Z-basis error</div><div className="metric-value">{result.basis_statistics?.Z.error_rate==null?'N/A':`${(result.basis_statistics.Z.error_rate*100).toFixed(2)}%`}</div></div><div className="metric"><div className="metric-label">X-basis error</div><div className="metric-value">{result.basis_statistics?.X.error_rate==null?'N/A':`${(result.basis_statistics.X.error_rate*100).toFixed(2)}%`}</div></div><div className="metric"><div className="metric-label">Mismatch rate</div><div className="metric-value">{result.mismatch_rate==null?'N/A':`${(result.mismatch_rate*100).toFixed(2)}%`}</div></div><div className="metric"><div className="metric-label">Authenticated verifier</div><div className="metric-value">{result.authenticated_verifier??'N/A'}</div></div><div className="metric"><div className="metric-label">Verification latency</div><div className="metric-value">{result.performance.verification_latency_ms.toFixed(2)} ms</div></div></div><div className="helper">Threshold: {(result.threshold*100).toFixed(1)}% [{result.threshold_source}] • Phase-sensitive evidence: {result.basis_statistics?.phase_sensitive_evidence?'YES':'NO'} • Failure code: {result.failure_code??'NONE'}</div></div></>}</section>
      <section className="card"><div className="card-header"><div><div className="card-title">Verifier guarantees</div><div className="card-kicker">What Bob checks</div></div><KeyRound size={18} color="var(--violet)"/></div><div className="card-body"><div className="session-list"><div className="session-row"><div><strong>DOCUMENT BINDING</strong><small>SHA-512 equality</small></div><CheckCircle2 size={15} color="var(--cyan)"/></div><div className="session-row"><div><strong>IDENTITY BINDING</strong><small>Alice → Bob session</small></div><CheckCircle2 size={15} color="var(--cyan)"/></div><div className="session-row"><div><strong>ONE-TIME NONCE</strong><small>Replay ledger</small></div><CheckCircle2 size={15} color="var(--cyan)"/></div><div className="session-row"><div><strong>QDS EVIDENCE</strong><small>Teleported-bit outcomes</small></div><CheckCircle2 size={15} color="var(--cyan)"/></div></div></div></section>
    </aside></div>
  </main></div>;
}

createRoot(document.getElementById('root')!).render(<React.StrictMode><BobApp/></React.StrictMode>);
