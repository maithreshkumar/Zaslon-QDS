import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Atom, User as UserIcon, Mail, Lock, Shield, AlertCircle, ArrowRight } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { UserRole } from '../types/auth';

export const RegisterPage: React.FC = () => {
  const { register } = useAuth();
  const navigate = useNavigate();
  const port = window.location.port;

  const defaultRole: UserRole = port === '5174' ? 'EVE' : port === '5175' ? 'BOB' : 'ALICE';

  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<UserRole>(defaultRole);
  const [publicIdentity, setPublicIdentity] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const getPortalInfo = () => {
    if (port === '5173') return { title: 'Alice Signer Portal (:5173) Registration', role: 'ALICE' as UserRole, badge: 'Alice (Signer)' };
    if (port === '5174') return { title: 'Eve Adversary Lab (:5174) Registration', role: 'EVE' as UserRole, badge: 'Eve (Attacker)' };
    if (port === '5175') return { title: 'Bob Verifier Portal (:5175) Registration', role: 'BOB' as UserRole, badge: 'Bob (Verifier)' };
    return { title: 'Register Role Identity', role: null, badge: null };
  };

  const portalInfo = getPortalInfo();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const targetRole = portalInfo.role || role;
      const user = await register({
        username,
        email,
        password,
        role: targetRole,
        public_identity: publicIdentity || undefined
      });
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
      setError(err.message || 'Registration failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-zaslon-950 text-slate-100 flex flex-col justify-center items-center p-6">
      <div className="w-full max-w-md bg-zaslon-900 border border-zaslon-800 rounded-2xl p-8 shadow-2xl backdrop-blur-md">
        <div className="flex flex-col items-center mb-6">
          <div className="w-12 h-12 rounded-xl bg-zaslon-950 border border-cyan-500/40 flex items-center justify-center mb-3">
            <Atom className="w-6 h-6 text-cyan-400 animate-spin-slow" />
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-slate-100 font-mono">
            {portalInfo.title}
          </h2>
          <p className="text-xs text-slate-400 mt-1 font-mono">
            {portalInfo.role ? `Role locked to terminal port :${port}` : 'Choose your role in the QDS protocol'}
          </p>
        </div>

        {error && (
          <div className="mb-6 p-3 rounded-lg bg-red-950/40 border border-red-500/40 text-red-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-mono text-slate-400 uppercase mb-1">Protocol Role</label>
            {portalInfo.badge ? (
              <div className={`py-2 px-3 rounded-lg text-xs font-mono border font-bold flex items-center justify-between ${
                portalInfo.role === 'ALICE'
                  ? 'bg-cyan-950/80 border-cyan-400 text-cyan-300'
                  : portalInfo.role === 'EVE'
                  ? 'bg-amber-950/80 border-amber-400 text-amber-300'
                  : 'bg-purple-950/80 border-purple-400 text-purple-300'
              }`}>
                <span>{portalInfo.badge}</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-zaslon-900 text-slate-400">PORT :{port} ONLY</span>
              </div>
            ) : (
              <div className="grid grid-cols-3 gap-2">
                <button
                  type="button"
                  onClick={() => setRole('ALICE')}
                  className={`py-2 px-3 rounded-lg text-xs font-mono border transition-all ${
                    role === 'ALICE'
                      ? 'bg-cyan-950/80 border-cyan-400 text-cyan-300 font-bold ring-1 ring-cyan-500/30'
                      : 'bg-zaslon-950 border-zaslon-700 text-slate-400 hover:border-slate-500'
                  }`}
                >
                  Alice (Signer)
                </button>
                <button
                  type="button"
                  onClick={() => setRole('EVE')}
                  className={`py-2 px-3 rounded-lg text-xs font-mono border transition-all ${
                    role === 'EVE'
                      ? 'bg-amber-950/80 border-amber-400 text-amber-300 font-bold ring-1 ring-amber-500/30'
                      : 'bg-zaslon-950 border-zaslon-700 text-slate-400 hover:border-slate-500'
                  }`}
                >
                  Eve (Attacker)
                </button>
                <button
                  type="button"
                  onClick={() => setRole('BOB')}
                  className={`py-2 px-3 rounded-lg text-xs font-mono border transition-all ${
                    role === 'BOB'
                      ? 'bg-purple-950/80 border-purple-400 text-purple-300 font-bold ring-1 ring-purple-500/30'
                      : 'bg-zaslon-950 border-zaslon-700 text-slate-400 hover:border-slate-500'
                  }`}
                >
                  Bob (Verifier)
                </button>
              </div>
            )}
          </div>

          <div>
            <label className="block text-xs font-mono text-slate-400 uppercase mb-1">Username</label>
            <div className="relative">
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                placeholder="e.g. alice_signer"
                className="w-full bg-zaslon-950 border border-zaslon-700 rounded-lg px-3 py-2 pl-9 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-cyan-500 font-mono"
              />
              <UserIcon className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
            </div>
          </div>

          <div>
            <label className="block text-xs font-mono text-slate-400 uppercase mb-1">Email</label>
            <div className="relative">
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                placeholder="user@zaslon.internal"
                className="w-full bg-zaslon-950 border border-zaslon-700 rounded-lg px-3 py-2 pl-9 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-cyan-500 font-mono"
              />
              <Mail className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
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
                placeholder="Minimum 6 characters"
                className="w-full bg-zaslon-950 border border-zaslon-700 rounded-lg px-3 py-2 pl-9 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-cyan-500 font-mono"
              />
              <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
            </div>
          </div>

          <div>
            <label className="block text-xs font-mono text-slate-400 uppercase mb-1">
              Public Designation (Optional)
            </label>
            <div className="relative">
              <input
                type="text"
                value={publicIdentity}
                onChange={(e) => setPublicIdentity(e.target.value)}
                placeholder="e.g. Alice Hamilton (Defense Directorate)"
                className="w-full bg-zaslon-950 border border-zaslon-700 rounded-lg px-3 py-2 pl-9 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-cyan-500 font-mono"
              />
              <Shield className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-2.5 px-4 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-mono text-sm font-bold transition-colors flex items-center justify-center gap-2 mt-2 disabled:opacity-50"
          >
            <span>{isSubmitting ? 'Registering...' : 'Register & Enter Portal'}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </form>

        <div className="mt-6 text-center text-xs font-mono text-slate-500">
          Already registered?{' '}
          <Link to="/login" className="text-cyan-400 hover:underline">
            Sign in
          </Link>
        </div>
      </div>
    </div>
  );
};
