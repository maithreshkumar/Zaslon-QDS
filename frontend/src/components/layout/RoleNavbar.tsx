import React from 'react';
import { Link } from 'react-router-dom';
import { Shield, Atom, LogOut, User as UserIcon, Lock } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { UserRole } from '../../types/auth';

export const RoleNavbar: React.FC = () => {
  const { user, logout } = useAuth();

  const getRoleBadge = (role?: UserRole) => {
    switch (role) {
      case 'ALICE':
        return {
          bg: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
          dot: 'bg-cyan-400',
          label: 'ALICE — SIGNER',
          accent: 'border-cyan-500'
        };
      case 'EVE':
        return {
          bg: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
          dot: 'bg-amber-400',
          label: 'EVE — ADVERSARY LAB',
          accent: 'border-amber-500'
        };
      case 'BOB':
        return {
          bg: 'bg-purple-500/10 text-purple-400 border-purple-500/30',
          dot: 'bg-purple-400',
          label: 'BOB — VERIFIER',
          accent: 'border-purple-500'
        };
      case 'ADMIN':
      default:
        return {
          bg: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
          dot: 'bg-emerald-400',
          label: 'RESEARCH / AUDITOR',
          accent: 'border-emerald-500'
        };
    }
  };

  const badge = getRoleBadge(user?.role);

  return (
    <header className="bg-zaslon-900 border-b border-zaslon-800 sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <Link to="/" className="flex items-center gap-3 hover:opacity-90 transition-opacity">
            <div className="relative flex items-center justify-center w-10 h-10 rounded-lg bg-zaslon-950 border border-zaslon-700 shadow-inner">
              <Atom className="w-6 h-6 text-cyan-400 animate-spin-slow" />
              <Shield className="w-3.5 h-3.5 text-zaslon-400 absolute bottom-1 right-1" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono font-bold text-lg tracking-wider text-slate-100">
                  ZASLON<span className="text-cyan-400">-QDS</span>
                </span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-zaslon-800 text-slate-400 font-mono">
                  SIH 26141
                </span>
              </div>
              <p className="text-[10px] text-slate-400 tracking-tight font-sans hidden sm:block">
                Quantum-Teleportation Threat Detection for QDS
              </p>
            </div>
          </Link>
        </div>

        {/* Center: Role Identity Badge */}
        {user && (
          <div className="hidden md:flex items-center gap-2">
            <span className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono font-medium border ${badge.bg}`}>
              <span className={`w-2 h-2 rounded-full ${badge.dot} animate-pulse`}></span>
              {badge.label}
            </span>
          </div>
        )}

        {/* Right: Port Indicator + User Profile + Actions */}
        <div className="flex items-center gap-3">
          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-zaslon-950 border border-zaslon-800 text-[11px] font-mono text-slate-400">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse"></span>
            <span>PORT {window.location.port ? `:${window.location.port}` : ':3000'}</span>
          </div>

          {user ? (
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-zaslon-950/60 border border-zaslon-800 text-xs font-mono text-slate-300">
                <UserIcon className="w-3.5 h-3.5 text-slate-400" />
                <span className="font-semibold">{user.public_identity || user.username}</span>
              </div>
              {window.location.port === '5173' || window.location.port === '5174' || window.location.port === '5175' ? (
                <div
                  className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-zaslon-950 border border-cyan-500/30 text-cyan-400/90 text-xs font-mono"
                  title="Actor identity is locked to this portal port"
                >
                  <Lock className="w-3.5 h-3.5 text-cyan-400" />
                  <span className="hidden sm:inline">PORT-LOCKED</span>
                </div>
              ) : (
                <button
                  onClick={logout}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-zaslon-950 border border-zaslon-800 hover:border-red-500/40 hover:bg-red-950/20 text-slate-400 hover:text-red-400 transition-colors text-xs font-mono"
                  title="Sign out of current identity"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">Logout</span>
                </button>
              )}
            </div>
          ) : (
            !(window.location.port === '5173' || window.location.port === '5174' || window.location.port === '5175') && (
              <div className="flex items-center gap-2">
                <Link
                  to="/login"
                  className="px-3 py-1.5 text-xs font-mono rounded-lg border border-zaslon-700 bg-zaslon-800 hover:bg-zaslon-700 text-slate-200 transition-colors"
                >
                  Login
                </Link>
                <Link
                  to="/register"
                  className="px-3 py-1.5 text-xs font-mono rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold transition-colors"
                >
                  Register
                </Link>
              </div>
            )
          )}
        </div>
      </div>
    </header>
  );
};
