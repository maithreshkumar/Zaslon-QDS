import React from 'react';
import {
  LayoutDashboard,
  Layers,
  GitFork,
  Radio,
  ShieldAlert,
  CheckCircle2,
  FileClock,
} from 'lucide-react';

export type TabType =
  | 'dashboard'
  | 'sessions'
  | 'workflow'
  | 'teleportation'
  | 'attacks'
  | 'verification'
  | 'audit';

interface SidebarProps {
  currentTab: TabType;
  onSelectTab: (tab: TabType) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentTab, onSelectTab }) => {
  const navItems: { id: TabType; label: string; icon: React.ReactNode }[] = [
    { id: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard className="w-4 h-4" /> },
    { id: 'sessions', label: 'Sessions', icon: <Layers className="w-4 h-4" /> },
    { id: 'workflow', label: 'QDS Pipeline', icon: <GitFork className="w-4 h-4" /> },
    { id: 'teleportation', label: 'Teleportation', icon: <Radio className="w-4 h-4" /> },
    { id: 'verification', label: 'Verification', icon: <CheckCircle2 className="w-4 h-4" /> },
    { id: 'attacks', label: 'Threat Simulator', icon: <ShieldAlert className="w-4 h-4" /> },
    { id: 'audit', label: 'Audit Trail', icon: <FileClock className="w-4 h-4" /> },
  ];

  return (
    <aside className="w-64 border-r border-zaslon-border bg-zaslon-900/50 flex flex-col justify-between shrink-0">
      <div className="p-4 space-y-1">
        <div className="px-3 py-2 text-[10px] font-mono uppercase tracking-wider text-slate-500 font-semibold">
          Platform Navigation
        </div>
        {navItems.map((item) => {
          const isActive = currentTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onSelectTab(item.id)}
              className={`w-full flex items-center space-x-3 px-3.5 py-2.5 rounded-lg text-xs font-medium transition-colors ${
                isActive
                  ? 'bg-zaslon-800 text-zaslon-quantum border border-zaslon-border'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-zaslon-850'
              }`}
            >
              <span className={isActive ? 'text-zaslon-quantum' : 'text-slate-400'}>
                {item.icon}
              </span>
              <span>{item.label}</span>
            </button>
          );
        })}
      </div>

      <div className="p-4 border-t border-zaslon-border/60">
        <div className="p-3 rounded-lg bg-zaslon-850/60 border border-zaslon-border text-[11px] text-slate-400 space-y-1">
          <div className="font-semibold text-slate-300">Quantum Protocol</div>
          <div className="text-slate-500 leading-tight">
            3-Qubit Teleportation &bull; SHA-512 &bull; Fisher Exact Test
          </div>
        </div>
      </div>
    </aside>
  );
};
