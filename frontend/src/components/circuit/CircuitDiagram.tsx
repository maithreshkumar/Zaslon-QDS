import React from 'react';
import { CheckCircle, AlertTriangle } from 'lucide-react';

interface CircuitDiagramProps {
  operationIndex?: number;
  theta?: number;
  phi?: number;
  basis?: string;
  m0?: number;
  m1?: number;
  bobObserved?: number;
  expectedBit?: number;
}

export const CircuitDiagram: React.FC<CircuitDiagramProps> = ({
  operationIndex,
  theta = 0,
  phi = 0,
  basis = 'Z',
  m0,
  m1,
  bobObserved,
  expectedBit,
}) => {
  const isMatch = bobObserved !== undefined && expectedBit !== undefined && bobObserved === expectedBit;
  const isEvaluated = bobObserved !== undefined && expectedBit !== undefined;

  return (
    <div className="p-5 rounded-xl border border-zaslon-border bg-zaslon-900/70 shadow-lg space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-zaslon-border/60 pb-3">
        <div className="flex items-center space-x-2.5">
          <span className="w-2 h-2 rounded-full bg-zaslon-quantum" />
          <h4 className="text-xs font-mono uppercase tracking-wider text-slate-300 font-semibold">
            3-Qubit Quantum Teleportation Circuit Topology
            {operationIndex !== undefined && (
              <span className="text-zaslon-quantum ml-1.5 font-bold">#Operation {operationIndex}</span>
            )}
          </h4>
        </div>

        <div className="flex items-center space-x-4 text-xs font-mono">
          <div className="flex items-center space-x-1.5">
            <span className="text-slate-500">Basis:</span>
            <span className="px-1.5 py-0.5 rounded bg-zaslon-800 border border-zaslon-border text-zaslon-quantum font-bold">
              {basis}
            </span>
          </div>
          <div className="text-slate-400">
            θ: <span className="text-slate-200">{theta.toFixed(3)} rad</span>
          </div>
          <div className="text-slate-400">
            φ: <span className="text-slate-200">{phi.toFixed(3)} rad</span>
          </div>

          {isEvaluated && (
            <div
              className={`flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] font-bold font-mono border ${
                isMatch
                  ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
                  : 'bg-rose-500/20 text-rose-400 border-rose-500/30'
              }`}
            >
              {isMatch ? (
                <>
                  <CheckCircle className="w-3.5 h-3.5" />
                  <span>FIDELITY 1.0 (MATCH)</span>
                </>
              ) : (
                <>
                  <AlertTriangle className="w-3.5 h-3.5" />
                  <span>MISMATCH DETECTED</span>
                </>
              )}
            </div>
          )}
        </div>
      </div>

      {/* SVG Diagram Canvas */}
      <div className="overflow-x-auto py-2">
        <svg viewBox="0 0 860 220" className="w-full max-w-5xl text-slate-300 font-mono text-[11px] select-none">
          {/* Wire 0: Message Qubit */}
          <text x="15" y="45" fill="#94a3b8" fontWeight="600">q[0] (Msg)</text>
          <line x1="95" y1="40" x2="520" y2="40" stroke="#334155" strokeWidth="2" />
          {/* Classical wire after M0 */}
          <line x1="520" y1="38" x2="820" y2="38" stroke="#64748b" strokeWidth="1.5" strokeDasharray="4 3" />
          <line x1="520" y1="42" x2="820" y2="42" stroke="#64748b" strokeWidth="1.5" strokeDasharray="4 3" />

          {/* Wire 1: Alice Bell Qubit */}
          <text x="15" y="105" fill="#94a3b8" fontWeight="600">q[1] (Alice)</text>
          <line x1="95" y1="100" x2="520" y2="100" stroke="#334155" strokeWidth="2" />
          {/* Classical wire after M1 */}
          <line x1="520" y1="98" x2="820" y2="98" stroke="#64748b" strokeWidth="1.5" strokeDasharray="4 3" />
          <line x1="520" y1="102" x2="820" y2="102" stroke="#64748b" strokeWidth="1.5" strokeDasharray="4 3" />

          {/* Wire 2: Bob Target Qubit */}
          <text x="15" y="165" fill="#94a3b8" fontWeight="600">q[2] (Bob)</text>
          <line x1="95" y1="160" x2="740" y2="160" stroke="#334155" strokeWidth="2" />
          <line x1="740" y1="158" x2="820" y2="158" stroke="#64748b" strokeWidth="1.5" strokeDasharray="4 3" />
          <line x1="740" y1="162" x2="820" y2="162" stroke="#64748b" strokeWidth="1.5" strokeDasharray="4 3" />

          {/* 1. State Prep Gate on q[0] */}
          <rect x="110" y="20" width="75" height="40" rx="4" fill="#0f172a" stroke="#0284c7" strokeWidth="1.5" />
          <text x="147" y="44" textAnchor="middle" fill="#38bdf8" fontWeight="600">U(θ,φ)</text>

          {/* 2. Bell Pair Gen: H on q[1], CNOT q[1]->q[2] */}
          <rect x="150" y="80" width="40" height="40" rx="4" fill="#0f172a" stroke="#38bdf8" strokeWidth="1.5" />
          <text x="170" y="105" textAnchor="middle" fill="#38bdf8" fontWeight="bold">H</text>

          <line x1="230" y1="100" x2="230" y2="160" stroke="#38bdf8" strokeWidth="2" />
          <circle cx="230" cy="100" r="4" fill="#38bdf8" />
          <circle cx="230" cy="160" r="10" fill="#0f172a" stroke="#38bdf8" strokeWidth="2" />
          <line x1="230" y1="154" x2="230" y2="166" stroke="#38bdf8" strokeWidth="2" />
          <line x1="224" y1="160" x2="236" y2="160" stroke="#38bdf8" strokeWidth="2" />

          {/* 3. Alice Entanglement: CNOT q[0]->q[1], H on q[0] */}
          <line x1="310" y1="40" x2="310" y2="100" stroke="#e2e8f0" strokeWidth="2" />
          <circle cx="310" cy="40" r="4" fill="#e2e8f0" />
          <circle cx="310" cy="100" r="10" fill="#0f172a" stroke="#e2e8f0" strokeWidth="2" />
          <line x1="310" y1="94" x2="310" y2="106" stroke="#e2e8f0" strokeWidth="2" />
          <line x1="304" y1="100" x2="316" y2="100" stroke="#e2e8f0" strokeWidth="2" />

          <rect x="360" y="20" width="40" height="40" rx="4" fill="#0f172a" stroke="#e2e8f0" strokeWidth="1.5" />
          <text x="380" y="45" textAnchor="middle" fill="#f8fafc" fontWeight="bold">H</text>

          {/* 4. Measurements: M0 on q[0], M1 on q[1] */}
          <rect x="440" y="20" width="44" height="40" rx="4" fill="#1e293b" stroke="#64748b" strokeWidth="1.5" />
          <text x="462" y="44" textAnchor="middle" fill="#f8fafc" fontWeight="bold">M₀</text>
          {m0 !== undefined && (
            <text x="462" y="14" textAnchor="middle" fill={m0 === 1 ? '#38bdf8' : '#94a3b8'} fontWeight="bold">
              m₀={m0}
            </text>
          )}

          <rect x="440" y="80" width="44" height="40" rx="4" fill="#1e293b" stroke="#64748b" strokeWidth="1.5" />
          <text x="462" y="104" textAnchor="middle" fill="#f8fafc" fontWeight="bold">M₁</text>
          {m1 !== undefined && (
            <text x="462" y="74" textAnchor="middle" fill={m1 === 1 ? '#38bdf8' : '#94a3b8'} fontWeight="bold">
              m₁={m1}
            </text>
          )}

          {/* 5. Classical Feed-forward Corrections on q[2]: X if m1, Z if m0 */}
          {/* Feed-forward connection lines */}
          <line
            x1="484"
            y1="100"
            x2="560"
            y2="140"
            stroke={m1 === 1 ? '#38bdf8' : '#475569'}
            strokeWidth="1.5"
            strokeDasharray="4 3"
          />
          <line
            x1="484"
            y1="40"
            x2="640"
            y2="140"
            stroke={m0 === 1 ? '#38bdf8' : '#475569'}
            strokeWidth="1.5"
            strokeDasharray="4 3"
          />

          <rect
            x="540"
            y="140"
            width="55"
            height="40"
            rx="4"
            fill="#0f172a"
            stroke={m1 === 1 ? '#38bdf8' : '#475569'}
            strokeWidth={m1 === 1 ? 2 : 1.5}
          />
          <text x="567" y="164" textAnchor="middle" fill={m1 === 1 ? '#38bdf8' : '#cbd5e1'} fontWeight="600">
            X^({m1 !== undefined ? m1 : 'm₁'})
          </text>

          <rect
            x="620"
            y="140"
            width="55"
            height="40"
            rx="4"
            fill="#0f172a"
            stroke={m0 === 1 ? '#38bdf8' : '#475569'}
            strokeWidth={m0 === 1 ? 2 : 1.5}
          />
          <text x="647" y="164" textAnchor="middle" fill={m0 === 1 ? '#38bdf8' : '#cbd5e1'} fontWeight="600">
            Z^({m0 !== undefined ? m0 : 'm₀'})
          </text>

          {/* 6. Bob Reconstructed Verification Measurement */}
          {basis === 'X' && (
            <>
              <rect x="690" y="140" width="30" height="40" rx="4" fill="#0f172a" stroke="#38bdf8" strokeWidth="1.5" />
              <text x="705" y="164" textAnchor="middle" fill="#38bdf8" fontWeight="bold">H</text>
            </>
          )}

          <rect
            x="735"
            y="140"
            width="50"
            height="40"
            rx="4"
            fill="#1e293b"
            stroke={isMatch ? '#10b981' : isEvaluated ? '#f43f5e' : '#64748b'}
            strokeWidth="2"
          />
          <text
            x="760"
            y="164"
            textAnchor="middle"
            fill={isMatch ? '#10b981' : isEvaluated ? '#f43f5e' : '#f8fafc'}
            fontWeight="bold"
          >
            M_Bob
          </text>

          {bobObserved !== undefined && (
            <text
              x="760"
              y="126"
              textAnchor="middle"
              fill={isMatch ? '#10b981' : '#f43f5e'}
              fontWeight="bold"
            >
              obs={bobObserved} (exp={expectedBit})
            </text>
          )}
        </svg>
      </div>

      <div className="p-3 rounded-lg bg-zaslon-850/40 border border-zaslon-border text-[11px] font-mono text-slate-400 flex flex-wrap items-center justify-between gap-2">
        <div>
          <span className="text-slate-500 font-semibold">Feed-Forward Correction Rule: </span>
          <span className="text-slate-200">U_corr = X^(m₁) &bull; Z^(m₀)</span>
        </div>
        <div className="text-slate-400">
          Theoretical Invariant:{' '}
          <span className="text-zaslon-quantum font-semibold">
            Bob's post-correction state |ψ_Bob⟩ ≡ |ψ_in⟩
          </span>
        </div>
      </div>
    </div>
  );
};
