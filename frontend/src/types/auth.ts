export type UserRole = 'ALICE' | 'EVE' | 'BOB' | 'ADMIN';

export interface User {
  id: string;
  username: string;
  email: string;
  role: UserRole;
  public_identity: string;
  status: string;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface TransmissionPackage {
  id: string;
  package_tracking_no: string;
  session_id: string;
  sender_id: string;
  recipient_id: string;
  status: 'DRAFT' | 'SIGNED' | 'IN_TRANSIT' | 'INTERCEPTED' | 'PASSTHROUGH' | 'MODIFIED' | 'FORWARDED' | 'RECEIVED' | 'VERIFIED' | 'REJECTED';
  message_payload: string;
  committed_digest: string;
  declaration_id?: string;
  signature_token: string;
  declaration_payload_hash?: string;
  quantum_run_id?: string;
  intercepted_by?: string;
  intercepted_at?: string;
  is_tampered: boolean;
  attack_type?: string;
  tamper_details?: Record<string, any>;
  forwarded_at?: string;
  delivered_at?: string;
  file_name?: string;
  file_mime_type?: string;
  file_size_bytes?: number;
  qds_manifest_json?: Record<string, any>;
  classical_channel_status?: string;
  quantum_channel_status?: string;
  tampered_channel?: string;
  active_attack_vector?: string;
  created_at: string;
}
