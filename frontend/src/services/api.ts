import {
  StandardResponse,
  Session,
  HashRecord,
  QuantumRun,
  QuantumStatusResponse,
  Measurement,
  PublicDeclaration,
  VerificationResult,
  VerificationSample,
  AttackEvent,
  AuditEvent,
  WorkflowOverview,
} from '../types';

const BASE_URL = '/api/v1';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  const json: StandardResponse<T> = await response.json();
  if (!response.ok || !json.success) {
    throw new Error(json.error || `HTTP error ${response.status}`);
  }
  return json.data;
}

export const api = {
  // Health
  checkHealth: () => request<any>('/health'),

  // Sessions
  createSession: (session_name: string, created_by: string, verifier_id: string) =>
    request<Session>('/sessions', {
      method: 'POST',
      body: JSON.stringify({ session_name, created_by, verifier_id }),
    }),

  listSessions: (limit = 50, offset = 0) =>
    request<Session[]>(`/sessions?limit=${limit}&offset=${offset}`),

  getSession: (sessionId: string) =>
    request<Session>(`/sessions/${sessionId}`),

  // Workflow & Hash
  computeHash: (sessionId: string, raw_message: string, actor: string) =>
    request<HashRecord>(`/sessions/${sessionId}/hash`, {
      method: 'POST',
      body: JSON.stringify({ raw_message, actor }),
    }),

  getWorkflowOverview: (sessionId: string) =>
    request<WorkflowOverview>(`/sessions/${sessionId}/workflow`),

  // Quantum Teleportation
  launchTeleportation: (sessionId: string, actor: string, count = 4096, batchSize = 512, background = false) =>
    request<QuantumRun>(`/sessions/${sessionId}/teleport?background=${background}`, {
      method: 'POST',
      body: JSON.stringify({ actor, teleportation_count: count, batch_size: batchSize }),
    }),

  getQuantumStatus: (sessionId: string) =>
    request<QuantumStatusResponse>(`/sessions/${sessionId}/quantum-status`),

  getQuantumRuns: (sessionId: string) =>
    request<QuantumRun[]>(`/sessions/${sessionId}/quantum-runs`),

  getMeasurements: (sessionId: string, page = 1, pageSize = 50) =>
    request<{ items: Measurement[]; total: number; page: number; page_size: number }>(
      `/sessions/${sessionId}/measurements?page=${page}&page_size=${pageSize}`
    ),

  // Public Declaration
  issueDeclaration: (sessionId: string, signer_id: string) =>
    request<PublicDeclaration>(`/sessions/${sessionId}/declare`, {
      method: 'POST',
      body: JSON.stringify({ signer_id }),
    }),

  getDeclaration: (sessionId: string) =>
    request<PublicDeclaration>(`/sessions/${sessionId}/declaration`),

  // Verification
  verifySession: (sessionId: string, verifier_id: string, sample_ratio = 0.05) =>
    request<VerificationResult>(`/sessions/${sessionId}/verify`, {
      method: 'POST',
      body: JSON.stringify({ verifier_id, sample_ratio }),
    }),

  getVerificationResults: (sessionId: string) =>
    request<VerificationResult[]>(`/sessions/${sessionId}/verification-results`),

  getVerificationSamples: (sessionId: string) =>
    request<VerificationSample[]>(`/sessions/${sessionId}/samples`),

  // Attacks
  simulateAttack: (sessionId: string, attack_type: string, tamper_payload?: Record<string, any>) =>
    request<AttackEvent>(`/sessions/${sessionId}/simulate-attack`, {
      method: 'POST',
      body: JSON.stringify({ attack_type, tamper_payload }),
    }),

  getAttackEvents: (sessionId: string) =>
    request<AttackEvent[]>(`/sessions/${sessionId}/attack-events`),

  // Audit
  getAuditTrail: (sessionId?: string, limit = 100) =>
    request<AuditEvent[]>(`/audit-trail?limit=${limit}${sessionId ? `&session_id=${sessionId}` : ''}`),
};
