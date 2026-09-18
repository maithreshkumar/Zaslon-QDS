export interface StandardResponse<T> {
  success: boolean;
  data: T;
  error?: string | null;
  code?: string | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export type SessionStatus =
  | 'CREATED'
  | 'HASHING'
  | 'HASHED'
  | 'STATE_PREPARATION'
  | 'TELEPORTING'
  | 'TELEPORTED'
  | 'DECLARATION_READY'
  | 'SAMPLING'
  | 'VERIFYING'
  | 'VERIFIED'
  | 'REJECTED'
  | 'FAILED';

export interface Participant {
  id: string;
  session_id: string;
  name: string;
  role: 'Signer' | 'Verifier' | 'Administrator';
  public_key_fingerprint: string;
  created_at: string;
}

export interface Session {
  id: string;
  session_name: string;
  status: SessionStatus;
  created_by: string;
  verifier_id: string;
  created_at: string;
  updated_at: string;
  participants: Participant[];
}

export interface HashRecord {
  id: string;
  session_id: string;
  message_bytes_len: number;
  sha512_digest: string;
  hash_encoding_format: string;
  created_at: string;
}

export interface QuantumRun {
  id: string;
  session_id: string;
  target_backend: string;
  teleportation_count: number;
  batch_size: number;
  completed_operations?: number;
  failed_operations?: number;
  current_batch?: number;
  total_batches?: number;
  execution_duration_ms?: number;
  status: 'PENDING' | 'PREPARING' | 'RUNNING' | 'PROCESSING_RESULTS' | 'COMPLETED' | 'FAILED';
  error_message?: string;
  created_at: string;
  completed_at?: string;
}

export interface QuantumStatusResponse {
  quantum_run_id: string;
  session_id: string;
  status: 'PENDING' | 'PREPARING' | 'RUNNING' | 'PROCESSING_RESULTS' | 'COMPLETED' | 'FAILED';
  teleportation_count: number;
  batch_size: number;
  completed_operations: number;
  failed_operations: number;
  current_batch: number;
  total_batches: number;
  progress_percentage: number;
  execution_duration_ms?: number | null;
  error_message?: string | null;
}

export interface Measurement {
  id: number;
  quantum_run_id: string;
  operation_index: number;
  prep_theta: number;
  prep_phi: number;
  expected_bit: number;
  alice_m0: number;
  alice_m1: number;
  bob_correction_x: number;
  bob_correction_z: number;
  bob_observed_bit: number;
  is_match: boolean;
}

export interface PublicDeclaration {
  id: string;
  session_id: string;
  signer_id: string;
  signature_token: string;
  declaration_payload_hash: string;
  declared_at: string;
  status: 'ACTIVE' | 'TAMPERED' | 'REVOKED';
  is_consumed: boolean;
  consumed_at?: string | null;
  consumed_in_verification_id?: string | null;
}

export interface VerificationSample {
  id: string;
  session_id: string;
  sample_ratio: number;
  sample_size: number;
  sample_seed: string;
  sampled_indices: number[];
  created_at: string;
}

export interface VerificationResult {
  id: string;
  session_id: string;
  sample_id: string | null;
  sample_size: number;
  match_count: number;
  mismatch_count: number;
  mismatch_ratio: number;
  fisher_p_value: number;
  fisher_odds_ratio: number | null;
  odds_ratio_display?: string;
  statistical_verdict: 'ACCEPTABLE' | 'SUSPICIOUS' | 'REJECTED';
  security_decision: 'VERIFIED' | 'REJECTED' | 'UNAUTHORIZED' | 'INTEGRITY_FAILURE';
  attack_detected: boolean;
  attack_category?: string;
  decision_reason: string;
  verified_at: string;
}

export interface AttackEvent {
  id: string;
  session_id: string;
  attack_type: 'FORGERY' | 'IMPERSONATION' | 'REPLAY' | 'UNAUTHORIZED_VERIFICATION' | 'INTEGRITY_TAMPERING';
  simulated: boolean;
  detected: boolean;
  payload_manipulation?: Record<string, any>;
  detection_evidence: Record<string, any>;
  created_at: string;
}

export interface AuditEvent {
  id: number;
  session_id?: string;
  event_type: string;
  actor: string;
  ip_address?: string;
  details: Record<string, any>;
  timestamp: string;
}

export interface WorkflowOverview {
  session_id: string;
  session_name: string;
  status: SessionStatus;
  created_by: string;
  verifier_id: string;
  stages: {
    hash_stage: {
      completed: boolean;
      sha512_digest?: string;
      message_len?: number;
    };
    quantum_stage: {
      completed: boolean;
      teleportation_count: number;
      duration_ms?: number;
      status: string;
    };
    declaration_stage: {
      completed: boolean;
      token?: string;
      status?: string;
    };
    verification_stage: {
      completed: boolean;
      decision?: string;
      mismatch_ratio?: number;
      fisher_p_value?: number;
      attack_detected: boolean;
    };
  };
}
