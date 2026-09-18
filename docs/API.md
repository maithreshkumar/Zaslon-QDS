# API Reference Specification — Zaslon-QDS

REST API v1 Contract Documentation for SIH 26141.

---

## 1. Response Envelope Format

Every API response adheres to a strict standard envelope:

```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "code": null
}
```

On failure:
```json
{
  "success": false,
  "data": null,
  "error": "Error explanation message",
  "code": "ERROR_CODE_IDENTIFIER",
  "details": { ... }
}
```

---

## 2. Core Endpoints Summary

### Health
- `GET /api/v1/health`
  - Returns component health for backend, database, and quantum microservice.

### Sessions
- `POST /api/v1/sessions`
  - Request: `{"session_name": string, "created_by": string, "verifier_id": string}`
  - Returns: Created session with initialized participants.
- `GET /api/v1/sessions?limit=50&offset=0`
  - Returns: List of active and archived sessions.
- `GET /api/v1/sessions/{session_id}`
  - Returns: Session details, status, and participant roster.

### QDS Workflow & Cryptography
- `POST /api/v1/sessions/{session_id}/hash`
  - Request: `{"raw_message": string, "actor": string}`
  - Computes SHA-512 and links hash record.
- `GET /api/v1/sessions/{session_id}/workflow`
  - Returns: Aggregated multi-stage workflow status.

### Quantum Teleportation
- `POST /api/v1/sessions/{session_id}/teleport`
  - Request: `{"actor": string, "teleportation_count": 4096, "batch_size": 512}`
  - Executes 4,096 3-qubit circuits on CUDA-Q microservice.
- `GET /api/v1/sessions/{session_id}/quantum-runs`
  - Returns: Run metadata, duration in milliseconds, and status.
- `GET /api/v1/sessions/{session_id}/measurements?page=1&page_size=50`
  - Returns: Paginated teleportation measurements (angles, Alice bits, Bob corrections, observed bit).

### Public Declaration
- `POST /api/v1/sessions/{session_id}/declare`
  - Request: `{"signer_id": string}`
  - Issues cryptographic public declaration commitment token.
- `GET /api/v1/sessions/{session_id}/declaration`
  - Returns: Active declaration record.

### Verification & Fisher Statistical Test
- `POST /api/v1/sessions/{session_id}/verify`
  - Request: `{"verifier_id": string, "sample_ratio": 0.05}`
  - Performs 5% sample extraction, mismatch calculation, Fisher's Exact Test, and cybersecurity evaluation.
- `GET /api/v1/sessions/{session_id}/verification-results`
  - Returns: Complete verification history for session.
- `GET /api/v1/sessions/{session_id}/samples`
  - Returns: Deterministic verification sample records and seeds.

### Cyber Threat Simulation
- `POST /api/v1/sessions/{session_id}/simulate-attack`
  - Request: `{"attack_type": "FORGERY" | "IMPERSONATION" | "REPLAY" | "UNAUTHORIZED_VERIFICATION" | "INTEGRITY_TAMPERING"}`
  - Mutates session data and passes it into verification pipeline.
- `GET /api/v1/sessions/{session_id}/attack-events`
  - Returns: Intercepted threat event logs.

### Audit Trail
- `GET /api/v1/audit-trail?session_id={id}&limit=100`
  - Returns: Tamper-evident audit trail entries.
