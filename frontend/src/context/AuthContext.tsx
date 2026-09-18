import React, { createContext, useContext, useState, useEffect } from 'react';
import { User, UserRole, AuthResponse } from '../types/auth';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<User>;
  register: (data: { username: string; email: string; password: string; role: UserRole; public_identity?: string }) => Promise<User>;
  quickDemoLogin: (role: UserRole) => Promise<User>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('zaslon_token'));
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    const initAuth = async () => {
      const port = window.location.port;
      const portRoleMap: Record<string, UserRole> = {
        '5173': 'ALICE',
        '5174': 'EVE',
        '5175': 'BOB'
      };

      const expectedRole = portRoleMap[port];

      // If running on a role-locked portal port (5173: Alice, 5174: Eve, 5175: Bob):
      if (expectedRole) {
        const savedToken = localStorage.getItem('zaslon_token');
        if (savedToken) {
          try {
            const res = await fetch('/api/v1/auth/me', {
              headers: { Authorization: `Bearer ${savedToken}` }
            });
            if (res.ok) {
              const userData = await res.json();
              if (userData.role === expectedRole) {
                setUser(userData);
                setToken(savedToken);
                setIsLoading(false);
                return;
              }
            }
          } catch {
            // Proceed to auto-fetch portal session
          }
        }

        // Auto-establish authentic port-bound actor session without exposing credentials
        try {
          const res = await fetch('/api/v1/auth/portal-session', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ port: parseInt(port, 10), role: expectedRole })
          });
          if (res.ok) {
            const data: AuthResponse = await res.json();
            localStorage.setItem('zaslon_token', data.access_token);
            setToken(data.access_token);
            setUser(data.user);
          }
        } catch (e) {
          console.error('Failed to establish portal session:', e);
        }
        setIsLoading(false);
        return;
      }

      // Default / Diagnostics port (3000 or custom)
      const savedToken = localStorage.getItem('zaslon_token');
      if (savedToken) {
        try {
          const res = await fetch('/api/v1/auth/me', {
            headers: { Authorization: `Bearer ${savedToken}` }
          });
          if (res.ok) {
            const userData = await res.json();
            setUser(userData);
            setToken(savedToken);
          } else {
            localStorage.removeItem('zaslon_token');
            setUser(null);
            setToken(null);
          }
        } catch {
          localStorage.removeItem('zaslon_token');
          setUser(null);
          setToken(null);
        }
      }
      setIsLoading(false);
    };

    initAuth();
  }, []);

  const login = async (username: string, password: string): Promise<User> => {
    const res = await fetch('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Login failed' }));
      throw new Error(err.detail || 'Authentication failed');
    }
    const data: AuthResponse = await res.json();
    localStorage.setItem('zaslon_token', data.access_token);
    setToken(data.access_token);
    setUser(data.user);
    return data.user;
  };

  const register = async (payload: { username: string; email: string; password: string; role: UserRole; public_identity?: string }): Promise<User> => {
    const res = await fetch('/api/v1/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Registration failed' }));
      throw new Error(err.detail || 'Registration failed');
    }
    const data: AuthResponse = await res.json();
    localStorage.setItem('zaslon_token', data.access_token);
    setToken(data.access_token);
    setUser(data.user);
    return data.user;
  };

  const quickDemoLogin = async (role: UserRole): Promise<User> => {
    // Ensure demo accounts are seeded
    await fetch('/api/v1/auth/seed-demo-users', { method: 'POST' }).catch(() => {});

    const usernameMap: Record<UserRole, string> = {
      ALICE: 'alice',
      EVE: 'eve',
      BOB: 'bob',
      ADMIN: 'admin'
    };
    return login(usernameMap[role], 'zaslon2026');
  };

  const logout = async () => {
    const port = window.location.port;
    const portRoleMap: Record<string, UserRole> = {
      '5173': 'ALICE',
      '5174': 'EVE',
      '5175': 'BOB'
    };
    if (portRoleMap[port]) {
      try {
        const res = await fetch('/api/v1/auth/portal-session', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ port: parseInt(port, 10), role: portRoleMap[port] })
        });
        if (res.ok) {
          const data: AuthResponse = await res.json();
          localStorage.setItem('zaslon_token', data.access_token);
          setToken(data.access_token);
          setUser(data.user);
          return;
        }
      } catch (e) {
        console.error('Portal session reset error:', e);
      }
    }
    localStorage.removeItem('zaslon_token');
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user,
        isLoading,
        login,
        register,
        quickDemoLogin,
        logout
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
