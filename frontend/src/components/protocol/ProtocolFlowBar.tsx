import React from 'react';
import { Send, ShieldAlert, CheckCircle2, ArrowRight } from 'lucide-react';
import { UserRole } from '../../types/auth';

interface ProtocolFlowBarProps {
  currentRole: UserRole;
  currentStage?: 'SIGNING' | 'IN_TRANSIT' | 'VERIFYING' | 'VERIFIED' | 'REJECTED';
}

export const ProtocolFlowBar: React.FC<ProtocolFlowBarProps> = ({ currentRole, currentStage }) => {
  return (
    <div className="bg-zaslon-900/80 border border-zaslon-800 rounded-lg p-3 px-4 mb-6 backdrop-blur-sm">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
          <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"></span>
          <span>QDS PROTOCOL LIFECYCLE{currentStage ? ` [${currentStage}]` : ''}:</span>
        </div>

        <div className="flex items-center gap-3 text-xs font-mono">
          {/* Stage 1: Alice */}
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded border ${
            currentRole === 'ALICE'
              ? 'bg-cyan-950/60 border-cyan-500 text-cyan-300 font-semibold ring-1 ring-cyan-500/30'
              : 'bg-zaslon-950/60 border-zaslon-800 text-slate-400'
          }`}>
            <Send className="w-3.5 h-3.5 text-cyan-400" />
            <span>1. ALICE (Signer)</span>
          </div>

          <ArrowRight className="w-3.5 h-3.5 text-slate-600 hidden sm:block" />

          {/* Stage 2: Eve */}
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded border ${
            currentRole === 'EVE'
              ? 'bg-amber-950/60 border-amber-500 text-amber-300 font-semibold ring-1 ring-amber-500/30'
              : 'bg-zaslon-950/60 border-zaslon-800 text-slate-400'
          }`}>
            <ShieldAlert className="w-3.5 h-3.5 text-amber-400" />
            <span>2. EVE (Adversary Lab)</span>
          </div>

          <ArrowRight className="w-3.5 h-3.5 text-slate-600 hidden sm:block" />

          {/* Stage 3: Bob */}
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded border ${
            currentRole === 'BOB'
              ? 'bg-purple-950/60 border-purple-500 text-purple-300 font-semibold ring-1 ring-purple-500/30'
              : 'bg-zaslon-950/60 border-zaslon-800 text-slate-400'
          }`}>
            <CheckCircle2 className="w-3.5 h-3.5 text-purple-400" />
            <span>3. BOB (Verifier)</span>
          </div>
        </div>
      </div>
    </div>
  );
};
