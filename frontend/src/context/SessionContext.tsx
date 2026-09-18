import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { Session } from '../types';
import { api } from '../services/api';

interface SessionContextType {
  currentSessionId: string | null;
  currentSession: Session | null;
  sessions: Session[];
  loading: boolean;
  error: string | null;
  selectSession: (sessionId: string) => void;
  refreshSessions: () => Promise<void>;
  refreshCurrentSession: () => Promise<void>;
  createSession: (name: string, signer: string, verifier: string) => Promise<Session>;
}

const SessionContext = createContext<SessionContextType | undefined>(undefined);

const STORAGE_KEY = 'zaslon_current_session_id';

export const SessionProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(() => {
    return localStorage.getItem(STORAGE_KEY);
  });
  const [currentSession, setCurrentSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshSessions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listSessions(50, 0);
      setSessions(data);

      if (data.length > 0) {
        const savedId = localStorage.getItem(STORAGE_KEY);
        const match = data.find((s) => s.id === savedId);
        if (match) {
          setCurrentSessionId(match.id);
          setCurrentSession(match);
        } else if (!savedId) {
          setCurrentSessionId(data[0].id);
          setCurrentSession(data[0]);
          localStorage.setItem(STORAGE_KEY, data[0].id);
        }
      }
    } catch (err: any) {
      console.error('Failed to list sessions:', err);
      setError(err.message || 'Failed to fetch sessions');
    } finally {
      setLoading(false);
    }
  }, []);

  const refreshCurrentSession = useCallback(async () => {
    if (!currentSessionId) {
      setCurrentSession(null);
      return;
    }
    try {
      const sess = await api.getSession(currentSessionId);
      setCurrentSession(sess);
    } catch (err: any) {
      console.error('Failed to get current session:', err);
    }
  }, [currentSessionId]);

  useEffect(() => {
    refreshSessions();
  }, [refreshSessions]);

  useEffect(() => {
    if (currentSessionId) {
      refreshCurrentSession();
    }
  }, [currentSessionId, refreshCurrentSession]);

  const selectSession = useCallback((sessionId: string) => {
    setCurrentSessionId(sessionId);
    localStorage.setItem(STORAGE_KEY, sessionId);
    const found = sessions.find((s) => s.id === sessionId);
    if (found) {
      setCurrentSession(found);
    } else {
      api.getSession(sessionId).then(setCurrentSession).catch(console.error);
    }
  }, [sessions]);

  const createSession = useCallback(
    async (name: string, signer: string, verifier: string) => {
      setLoading(true);
      setError(null);
      try {
        const newSession = await api.createSession(name, signer, verifier);
        setSessions((prev) => [newSession, ...prev]);
        setCurrentSessionId(newSession.id);
        setCurrentSession(newSession);
        localStorage.setItem(STORAGE_KEY, newSession.id);
        return newSession;
      } catch (err: any) {
        setError(err.message || 'Failed to create session');
        throw err;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  return (
    <SessionContext.Provider
      value={{
        currentSessionId,
        currentSession,
        sessions,
        loading,
        error,
        selectSession,
        refreshSessions,
        refreshCurrentSession,
        createSession,
      }}
    >
      {children}
    </SessionContext.Provider>
  );
};

export const useSession = (): SessionContextType => {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error('useSession must be used within a SessionProvider');
  }
  return context;
};
