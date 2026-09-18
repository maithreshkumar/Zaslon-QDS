import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Atom, ShieldAlert, CheckCircle2, ArrowRight, Lock, Cpu, BarChart2, Key } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { UserRole } from '../types/auth';

export const LandingPage: React.FC = () => {
  const { quickDemoLogin } = useAuth();
  const navigate = useNavigate();

  const handleLaunchRole = async (role: UserRole) => {
    try {
      await quickDemoLogin(role);
      const routes: Record<UserRole, string> = {
        ALICE: '/alice',
        EVE: '/eve',
        BOB: '/bob',
        ADMIN: '/research'
      };
      navigate(routes[role]);
    } catch (err) {
      console.error('Launch failed', err);
    }
  };

  return (
    <div className="min-h-screen bg-zaslon-950 text-slate-100 flex flex-col">
      {/* Top Navbar */}
      <header className="border-b border-zaslon-800 bg-zaslon-900/60 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-zaslon-950 border border-cyan-500/40 flex items-center justify-center">
              <Atom className="w-5 h-5 text-cyan-400 animate-spin-slow" />
            </div>
            <div>
              <span className="font-mono font-bold text-lg tracking-wider text-slate-100">
                ZASLON<span className="text-cyan-400">-QDS</span>
              </span>
              <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800 font-mono">
                SIH 26141
              </span>
            </div>
          </div>
          <div className="flex items-center gap-3 font-mono text-xs">
            <button
              onClick={() => navigate('/login')}
              className="px-4 py-2 rounded-lg border border-zaslon-700 bg-zaslon-800/80 hover:bg-zaslon-700 text-slate-200 transition-colors"
            >
              Sign In
            </button>
            <button
              onClick={() => navigate('/register')}
              className="px-4 py-2 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold transition-colors"
            >
              Register Role
            </button>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <main className="flex-1 max-w-7xl mx-auto px-6 py-12 flex flex-col items-center text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-cyan-500/30 bg-cyan-950/40 text-cyan-300 text-xs font-mono mb-6">
          <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"></span>
          REAL 3-QUBIT TELEPORTATION ON NVIDIA CUDA-Q — NO AI/ML — MATHEMATICALLY PROVABLE
        </div>

        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight max-w-4xl text-slate-100 leading-tight">
          Quantum-Teleportation-Based <br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-teal-300 to-indigo-400">
            Cyber Threat Detection for QDS
          </span>
        </h1>

        <p className="mt-6 text-base sm:text-lg text-slate-400 max-w-3xl leading-relaxed">
          Zaslon-QDS models the authentic multi-party interaction between <strong>Alice (Signer)</strong>,{' '}
          <strong>Eve (Adversary)</strong>, and <strong>Bob (Verifier)</strong>. 
          Signatures are bound to 4,096 quantum teleportation operations, SHA-512 cryptographic digests, and verified through hypergeometric Fisher hypothesis testing.
        </p>

        {/* 3-Actor Interactive Protocol Flow */}
        <div className="w-full max-w-5xl mt-12 mb-12 p-8 rounded-2xl bg-zaslon-900/60 border border-zaslon-800 backdrop-blur-md shadow-2xl">
          <div className="text-xs font-mono tracking-widest text-slate-400 uppercase mb-8">
            Three-Party Protocol Architecture
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 relative">
            {/* Card 1: Alice */}
            <div className="bg-zaslon-950/80 border border-cyan-500/40 rounded-xl p-6 text-left hover:border-cyan-400 transition-all group">
              <div className="w-12 h-12 rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center mb-4 group-hover:scale-105 transition-transform">
                <Key className="w-6 h-6 text-cyan-400" />
              </div>
              <div className="text-xs font-mono text-cyan-400 uppercase font-semibold">Stage 1: Signer</div>
              <h3 className="text-xl font-bold text-slate-100 mt-1">ALICE</h3>
              <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                Composes plaintext message, generates canonical SHA-512 digest, orchestrates 4,096 teleportation circuits on CUDA-Q, issues public declaration token, and dispatches in transit.
              </p>
              <button
                onClick={() => handleLaunchRole('ALICE')}
                className="mt-6 w-full py-2.5 px-4 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-mono text-xs font-bold flex items-center justify-center gap-2 transition-colors shadow-lg shadow-cyan-500/10"
              >
                <span>Launch as Alice (Signer)</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Card 2: Eve */}
            <div className="bg-zaslon-950/80 border border-amber-500/40 rounded-xl p-6 text-left hover:border-amber-400 transition-all group">
              <div className="w-12 h-12 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center mb-4 group-hover:scale-105 transition-transform">
                <ShieldAlert className="w-6 h-6 text-amber-400" />
              </div>
              <div className="text-xs font-mono text-amber-400 uppercase font-semibold">Stage 2: Adversary</div>
              <h3 className="text-xl font-bold text-slate-100 mt-1">EVE</h3>
              <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                Intercepts in-flight transmission. Can choose passthrough (unaltered) or inject 5 controlled cyber threats: Forgery, Impersonation, Replay, Unauthorized Verification, or Message Tampering.
              </p>
              <button
                onClick={() => handleLaunchRole('EVE')}
                className="mt-6 w-full py-2.5 px-4 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-mono text-xs font-bold flex items-center justify-center gap-2 transition-colors shadow-lg shadow-amber-500/10"
              >
                <span>Launch as Eve (Attacker)</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Card 3: Bob */}
            <div className="bg-zaslon-950/80 border border-purple-500/40 rounded-xl p-6 text-left hover:border-purple-400 transition-all group">
              <div className="w-12 h-12 rounded-xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center mb-4 group-hover:scale-105 transition-transform">
                <CheckCircle2 className="w-6 h-6 text-purple-400" />
              </div>
              <div className="text-xs font-mono text-purple-400 uppercase font-semibold">Stage 3: Verifier</div>
              <h3 className="text-xl font-bold text-slate-100 mt-1">BOB</h3>
              <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                Receives transmission package in inbox. Executes Zaslon-QDS 11-step verification framework: 5% sampling, Fisher's Exact Test, SHA-512 check, and RBAC defense barriers.
              </p>
              <button
                onClick={() => handleLaunchRole('BOB')}
                className="mt-6 w-full py-2.5 px-4 rounded-lg bg-purple-500 hover:bg-purple-400 text-slate-100 font-mono text-xs font-bold flex items-center justify-center gap-2 transition-colors shadow-lg shadow-purple-500/10"
              >
                <span>Launch as Bob (Verifier)</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          <div className="mt-8 pt-6 border-t border-zaslon-800 flex flex-wrap items-center justify-between gap-4 text-xs font-mono text-slate-400">
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-cyan-400" />
              <span>NVIDIA CUDA-Q 0.16.0 Engine</span>
            </div>
            <div className="flex items-center gap-2">
              <Lock className="w-4 h-4 text-amber-400" />
              <span>SHA-512 Cryptographic Binding</span>
            </div>
            <div className="flex items-center gap-2">
              <BarChart2 className="w-4 h-4 text-purple-400" />
              <span>Fisher Exact Test (alpha = 0.01)</span>
            </div>
            <button
              onClick={() => handleLaunchRole('ADMIN')}
              className="text-cyan-400 hover:text-cyan-300 underline underline-offset-4"
            >
              Open Research Diagnostics &rarr;
            </button>
          </div>
        </div>
      </main>
    </div>
  );
};
