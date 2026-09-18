import { useState, useEffect, useCallback, useRef } from 'react';
import { QuantumStatusResponse } from '../types';
import { api } from '../services/api';

interface UseQuantumStatusOptions {
  pollIntervalMs?: number;
  enabled?: boolean;
  onComplete?: (status: QuantumStatusResponse) => void;
  onFail?: (status: QuantumStatusResponse) => void;
}

export const useQuantumStatus = (
  sessionId: string | null,
  options: UseQuantumStatusOptions = {}
) => {
  const { pollIntervalMs = 1500, enabled = true, onComplete, onFail } = options;

  const [status, setStatus] = useState<QuantumStatusResponse | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const onCompleteRef = useRef(onComplete);
  const onFailRef = useRef(onFail);
  onCompleteRef.current = onComplete;
  onFailRef.current = onFail;

  const fetchStatus = useCallback(async (): Promise<QuantumStatusResponse | null> => {
    if (!sessionId) {
      setStatus(null);
      return null;
    }

    try {
      const data = await api.getQuantumStatus(sessionId);
      setStatus(data);
      setError(null);

      if (data.status === 'COMPLETED') {
        if (timerRef.current) {
          clearInterval(timerRef.current);
          timerRef.current = null;
        }
        setIsPolling(false);
        onCompleteRef.current?.(data);
      } else if (data.status === 'FAILED') {
        if (timerRef.current) {
          clearInterval(timerRef.current);
          timerRef.current = null;
        }
        setIsPolling(false);
        onFailRef.current?.(data);
      }

      return data;
    } catch (err: any) {
      // If 404/not yet run, status is just null without fatal error
      if (err.message && err.message.includes('404')) {
        setStatus(null);
      } else {
        setError(err.message || 'Failed to fetch quantum status');
      }
      return null;
    }
  }, [sessionId]);

  const startPolling = useCallback(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    setIsPolling(true);
    fetchStatus();
    timerRef.current = setInterval(fetchStatus, pollIntervalMs);
  }, [fetchStatus, pollIntervalMs]);

  const stopPolling = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    setIsPolling(false);
  }, []);

  useEffect(() => {
    if (!sessionId || !enabled) {
      stopPolling();
      setStatus(null);
      return;
    }

    // Initial fetch
    fetchStatus().then((current) => {
      if (
        current &&
        ['PENDING', 'PREPARING', 'RUNNING', 'PROCESSING_RESULTS'].includes(current.status)
      ) {
        startPolling();
      }
    });

    return () => {
      stopPolling();
    };
  }, [sessionId, enabled, fetchStatus, startPolling, stopPolling]);

  const isExecuting =
    status !== null &&
    ['PENDING', 'PREPARING', 'RUNNING', 'PROCESSING_RESULTS'].includes(status.status);

  return {
    status,
    isPolling,
    isExecuting,
    progressPercentage: status?.progress_percentage ?? 0,
    completedOperations: status?.completed_operations ?? 0,
    teleportationCount: status?.teleportation_count ?? 4096,
    currentBatch: status?.current_batch ?? 0,
    totalBatches: status?.total_batches ?? 0,
    error,
    refresh: fetchStatus,
    startPolling,
    stopPolling,
  };
};
