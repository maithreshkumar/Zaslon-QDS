import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { UserRole } from '../../types/auth';

interface ProtectedRouteProps {
  children: React.ReactNode;
  allowedRoles?: UserRole[];
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, allowedRoles }) => {
  const { user, isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-zaslon-950 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4 text-cyan-400">
          <div className="w-10 h-10 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin"></div>
          <p className="font-mono text-xs tracking-widest uppercase">Authenticating Zaslon-QDS Identity...</p>
        </div>
      </div>
    );
  }

  const isPortLocked = window.location.port === '5173' || window.location.port === '5174' || window.location.port === '5175';

  if (!isAuthenticated || !user) {
    if (isPortLocked) {
      return (
        <div className="min-h-screen bg-zaslon-950 flex items-center justify-center">
          <div className="flex flex-col items-center gap-4 text-cyan-400">
            <div className="w-10 h-10 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin"></div>
            <p className="font-mono text-xs tracking-widest uppercase">Connecting to Portal Session...</p>
          </div>
        </div>
      );
    }
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role) && user.role !== 'ADMIN') {
    if (isPortLocked) {
      return (
        <div className="min-h-screen bg-zaslon-950 flex items-center justify-center text-red-400 font-mono text-xs">
          PORT ROLE MISMATCH: Expected {allowedRoles.join(', ')} but authenticated as {user.role}.
        </div>
      );
    }
    const roleRedirects: Record<UserRole, string> = {
      ALICE: '/alice',
      EVE: '/eve',
      BOB: '/bob',
      ADMIN: '/research'
    };
    return <Navigate to={roleRedirects[user.role] || '/'} replace />;
  }

  return <>{children}</>;
};
