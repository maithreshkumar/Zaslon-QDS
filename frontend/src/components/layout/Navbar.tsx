import React, { useEffect, useState } from 'react';
import { Cpu, Database } from 'lucide-react';
import { api } from '../../services/api';
import { useSession } from '../../context/SessionContext';

interface NavbarProps {
  currentSessionId?: string | null;
}

export const Navbar: React.FC<NavbarProps> = () => {
  const { currentSession, currentSessionId } = useSession();
  const [healthStatus, setHealthStatus] = useState<'HEALTHY' | 'DEGRADED' | 'CHECKING'>('CHECKING');

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const res = await api.checkHealth();
        setHealthStatus(res.status === 'HEALTHY' ? 'HEALTHY' : 'DEGRADED');
      } catch (err) {
        setHealthStatus('DEGRADED');
      }
    };
    fetchHealth();
    const interval = setInterval(fetchHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="h-16 border-b border-zaslon-border bg-zaslon-900/80 backdrop-blur px-6 flex items-center justify-between sticky top-0 z-30">
      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-2">
          <div className="w-8 h-8 rounded-lg bg-zaslon-accent/20 border border-zaslon-accent/40 flex items-center justify-center text-zaslon-accent font-bold font-mono">
            Z
          </div>
          <div>
            <span className="font-semibold text-slate-100 tracking-wide">ZASLON-QDS</span>
            <span className="text-xs text-slate-400 ml-2 font-mono">SIH 26141</span>
          </div>
        </div>

        {currentSessionId && (
          <div className="hidden md:flex items-center space-x-2 px-3 py-1 rounded bg-zaslon-850 border border-zaslon-border text-xs font-mono text-slate-300">
            <span className="text-slate-500">ACTIVE SESSION:</span>
            <span className="text-zaslon-quantum font-medium">
              {currentSession?.session_name || `${currentSessionId.substring(0, 8)}...`}
            </span>
          </div>
        )}
      </div>

      <div className="flex items-center space-x-4 text-xs font-mono">
        <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-full border border-zaslon-border bg-zaslon-850">
          <div
            className={`w-2 h-2 rounded-full ${
              healthStatus === 'HEALTHY'
                ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]'
                : 'bg-amber-400'
            }`}
          />
          <span className="text-slate-300 font-medium">SYS: {healthStatus}</span>
        </div>

        <div className="hidden lg:flex items-center space-x-3 text-slate-400">
          <span className="flex items-center space-x-1">
            <Cpu className="w-3.5 h-3.5 text-zaslon-quantum" />
            <span>CUDA-Q ENGINE</span>
          </span>
          <span className="text-slate-600">|</span>
          <span className="flex items-center space-x-1">
            <Database className="w-3.5 h-3.5 text-slate-400" />
            <span>MYSQL 8.0</span>
          </span>
        </div>
      </div>
    </header>
  );
};
