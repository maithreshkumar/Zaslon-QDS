import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Atom, Lock, User as UserIcon, AlertCircle, ArrowRight } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { UserRole } from '../types/auth';

export const LoginPage: React.FC = () => {
  const { login, quickDemoLogin } = useAuth();
  const navigate = useNavigate();
  const port = window.location.port;

  const [username, setUsername] = useState(
    port === '5173' ? 'alice' : port === '5174' ? 'eve' : port === '5175' ? 'bob' : ''
  );
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const getPortalInfo = () => {
    if (port === '5173') return { title: 'Alice Signer Portal (:5173)', role: 'ALICE' as UserRole, color: 'text-cyan-400' };
    if (port === '5174') return { title: 'Eve Adversary Lab (:5174)', role: 'EVE' as UserRole, color: 'text-amber-400' };
    if (port === '5175') return { title: 'Bob Verifier Portal (:5175)', role: 'BOB' as UserRole, color: 'text-purple-400' };
    return { title: 'Authentication & Role Authorization', role: null, color: 'text-cyan-400' };
  };

  const portalInfo = getPortalInfo();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const user = await login(username, password);
      // On specific ports, redirect to root which loads the role portal
      if (port === '5173' || port === '5174' || port === '5175') {
        navigate('/');
      } else {
        const roleRedirects: Record<UserRole, string> = {
          ALICE: '/alice',
          EVE: '/eve',
          BOB: '/bob',
          ADMIN: '/research'
        };
        navigate(roleRedirects[user.role] || '/');
      }
    } catch (err: any) {
      setError(err.message || 'Login failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDemoLogin = async (role: UserRole) => {
    setError(null);
    setIsSubmitting(true);
    try {
      const user = await quickDemoLogin(role);
      if (port === '5173' || port === '5174' || port === '5175') {
        navigate('/');
      } else {
        const roleRedirects: Record<UserRole, string> = {
          ALICE: '/alice',
          EVE: '/eve',
          BOB: '/bob',
          ADMIN: '/research'
        };
        navigate(roleRedirects[user.role] || '/');
      }
    } catch (err: any) {
      setError(err.message || 'Demo login failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-zaslon-950 text-slate-100 flex flex-col justify-center items-center p-6">
      <div className="w-full max-w-md bg-zaslon-900 border border-zaslon-800 rounded-2xl p-8 shadow-2xl backdrop-blur-md">
        <div className="flex flex-col items-center mb-8">
          <div className="w-12 h-12 rounded-xl bg-zaslon-950 border border-cyan-500/40 flex items-center justify-center mb-3">
            <Atom className="w-6 h-6 text-cyan-400 animate-spin-slow" />
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-slate-100 font-mono">
            ZASLON<span className="text-cyan-400">-QDS</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1 font-mono">{portalInfo.title}</p>
        </div>

        {error && (
          <div className="mb-6 p-3 rounded-lg bg-red-950/40 border border-red-500/40 text-red-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-mono text-slate-400 uppercase mb-1">Username / Identifier</label>
            <div className="relative">
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                placeholder="alice, eve, or bob"
                className="w-full bg-zaslon-950 border border-zaslon-700 rounded-lg px-3 py-2.5 pl-9 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-cyan-500 font-mono"
              />
              <UserIcon className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
            </div>
          </div>

          <div>
            <label className="block text-xs font-mono text-slate-400 uppercase mb-1">Password</label>
            <div className="relative">
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                placeholder="Enter password"
                className="w-full bg-zaslon-950 border border-zaslon-700 rounded-lg px-3 py-2.5 pl-9 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-cyan-500 font-mono"
              />
              <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-2.5 px-4 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-mono text-sm font-bold transition-colors flex items-center justify-center gap-2 mt-2 disabled:opacity-50"
          >
            <span>{isSubmitting ? 'Authenticating...' : 'Sign In'}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </form>

        {/* Quick Demo Launchers */}
        <div className="mt-8 pt-6 border-t border-zaslon-800">
          <div className="text-[11px] font-mono text-slate-400 text-center uppercase tracking-wider mb-3">
            Quick 1-Click Role Login (Evaluators)
          </div>
          {port === '5173' ? (
            <button
              onClick={() => handleDemoLogin('ALICE')}
              disabled={isSubmitting}
              className="w-full p-2.5 rounded-lg bg-cyan-950/60 border border-cyan-500/50 hover:border-cyan-400 text-cyan-300 text-xs font-mono font-semibold transition-colors text-center"
            >
              Sign In as Alice (Signer) — Port :5173
            </button>
          ) : port === '5174' ? (
            <button
              onClick={() => handleDemoLogin('EVE')}
              disabled={isSubmitting}
              className="w-full p-2.5 rounded-lg bg-amber-950/60 border border-amber-500/50 hover:border-amber-400 text-amber-300 text-xs font-mono font-semibold transition-colors text-center"
            >
              Sign In as Eve (Attacker) — Port :5174
            </button>
          ) : port === '5175' ? (
            <button
              onClick={() => handleDemoLogin('BOB')}
              disabled={isSubmitting}
              className="w-full p-2.5 rounded-lg bg-purple-950/60 border border-purple-500/50 hover:border-purple-400 text-purple-300 text-xs font-mono font-semibold transition-colors text-center"
            >
              Sign In as Bob (Verifier) — Port :5175
            </button>
          ) : (
            <div className="grid grid-cols-3 gap-2">
              <button
                onClick={() => handleDemoLogin('ALICE')}
                disabled={isSubmitting}
                className="p-2 rounded-lg bg-cyan-950/40 border border-cyan-500/30 hover:border-cyan-400 text-cyan-300 text-xs font-mono transition-colors text-center"
              >
                Alice (Signer)
              </button>
              <button
                onClick={() => handleDemoLogin('EVE')}
                disabled={isSubmitting}
                className="p-2 rounded-lg bg-amber-950/40 border border-amber-500/30 hover:border-amber-400 text-amber-300 text-xs font-mono transition-colors text-center"
              >
                Eve (Attacker)
              </button>
              <button
                onClick={() => handleDemoLogin('BOB')}
                disabled={isSubmitting}
                className="p-2 rounded-lg bg-purple-950/40 border border-purple-500/30 hover:border-purple-400 text-purple-300 text-xs font-mono transition-colors text-center"
              >
                Bob (Verifier)
              </button>
            </div>
          )}
        </div>

        <div className="mt-6 text-center text-xs font-mono text-slate-500">
          Need a new identity?{' '}
          <Link to="/register" className="text-cyan-400 hover:underline">
            Register role
          </Link>
        </div>
      </div>
    </div>
  );
};
