# Zaslon-QDS — Cryptographic Signature Package Specification (`.qds.json`)
## SIH 26141 — Quantum-Teleportation-Based Cyber Threat Detection for QDS

---

## 1. Overview & Purpose

In **Zaslon-QDS**, every signed document generates a portable, standardized companion artifact: `<filename>.qds.json`.
This artifact constitutes the **classical envelope** of a Quantum Digital Signature, cryptographically binding the raw document payload to:
1. Exact-byte streaming SHA-512 message digest.
2. Signer public identity ($A_{\text{pub}}$).
3. Designated verifier public identity ($B_{\text{pub}}$).
4. Public declaration commitment token.
5. Unique session parameters and single-use anti-replay nonce.
6. Execution metadata of the underlying 4,096-operation NVIDIA CUDA-Q teleportation run.

The package is transmitted over the **Application-Level Classical Channel**, in parallel with the **Simulated Quantum Channel** carrying the physical Bell EPR correlations.

---

## 2. Core Architectural & Security Invariants

1. **Server-Authoritative Anti-Replay (`is_consumed` Invariant)**:
   - The `.qds.json` manifest **MUST NOT** include `"is_consumed"`.
   - Single-use token state is strictly server-authoritative and managed exclusively within the MySQL database (`public_declarations` table) protected by database row locks (`SELECT ... FOR UPDATE`).
   - Including a client-controlled `"is_consumed": false` flag inside the manifest would create a catastrophic client-side privilege escalation and anti-replay bypass vulnerability.

2. **Absence of Raw Quantum States**:
   - The `.qds.json` manifest **MUST NOT** embed the 4,096 individual qubit states, rotation angles, or mid-circuit measurements.
   - Doing so would allow an adversary inspecting the classical channel to forge measurement correlation without interacting with the quantum channel.
   - The manifest contains only the cryptographic commitment hash, run ID, and operation count ($N = 4096$).

3. **Absence of Verifier Private Sampling Secrets**:
   - Bob evaluates the quantum channel by deterministically sampling $\sim 5\%$ of operations ($N_{\text{sample}} = 205$).
   - The pseudo-random sampling seed is computed privately by Bob at verification time using session-bound HMAC.
   - The sample indices are strictly private to Bob and never revealed inside `.qds.json`.

4. **Exact-Byte Streaming SHA-512**:
   - The `sha512_digest` field is computed over the verbatim raw binary stream of the file (`payload.bin`) in 64KB chunks.
   - Text files, PDFs, images, and binary archives are treated identically as raw octet streams without encoding transformations.

5. **Standardized Project Identifiers**:
   - Format: `"ZASLON-QDS"`
   - Profile: `"ZASLON-QDS-v1"`
   - Project ID: `"SIH-26141"`

---

## 3. Storage Architecture

Signed packages are persisted on the host filesystem under a deterministic hierarchical directory structure:

```text
storage/
└── packages/
    └── <package_id>/
        ├── payload.bin          # Verbatim uploaded document bytes (<= 50 MB)
        ├── <filename>.qds.json  # Companion cryptographic signature package
        └── <filename>.cert.json # Post-verification cryptographic receipt (if verified)
```

- `payload.bin`: The exact raw bytes uploaded by Alice.
- `<filename>.qds.json`: Downloadable by Alice and Bob; inspectable by Eve on the classical channel.
- `<filename>.cert.json`: Generated post-verification upon successful Fisher exact test and 15-check validation.

---

## 4. Manifest JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "ZaslonQdsSignaturePackage",
  "type": "object",
  "required": [
    "format",
    "version",
    "project_id",
    "profile",
    "package_id",
    "session_id",
    "tracking_number",
    "document",
    "cryptographic_binding",
    "quantum_telemetry",
    "public_declaration",
    "transmission_envelope"
  ],
  "properties": {
    "format": { "type": "string", "const": "ZASLON-QDS" },
    "version": { "type": "string", "const": "1.0.0" },
    "project_id": { "type": "string", "const": "SIH-26141" },
    "profile": { "type": "string", "const": "ZASLON-QDS-v1" },
    "package_id": { "type": "string", "format": "uuid" },
    "session_id": { "type": "string", "format": "uuid" },
    "tracking_number": { "type": "string" },
    "document": {
      "type": "object",
      "required": ["filename", "file_size_bytes", "mime_type", "sha512_digest"],
      "properties": {
        "filename": { "type": "string" },
        "file_size_bytes": { "type": "integer", "minimum": 0, "maximum": 52428800 },
        "mime_type": { "type": "string" },
        "sha512_digest": { "type": "string", "pattern": "^[0-9a-f]{128}$" }
      }
    },
    "cryptographic_binding": {
      "type": "object",
      "required": ["signer_identity", "designated_verifier", "declaration_hash", "nonce", "signed_at"],
      "properties": {
        "signer_identity": { "type": "string" },
        "designated_verifier": { "type": "string" },
        "declaration_hash": { "type": "string", "pattern": "^[0-9a-f]{128}$" },
        "nonce": { "type": "string" },
        "signed_at": { "type": "string", "format": "date-time" }
      }
    },
    "quantum_telemetry": {
      "type": "object",
      "required": ["quantum_run_id", "teleportation_operations_count", "cuda_q_target", "principle_of_deferred_measurement"],
      "properties": {
        "quantum_run_id": { "type": "string", "format": "uuid" },
        "teleportation_operations_count": { "type": "integer", "const": 4096 },
        "cuda_q_target": { "type": "string" },
        "principle_of_deferred_measurement": { "type": "boolean", "const": true }
      }
    },
    "public_declaration": {
      "type": "object",
      "required": ["declaration_id", "signature_token", "commitment_type", "declared_at"],
      "properties": {
        "declaration_id": { "type": "string", "format": "uuid" },
        "signature_token": { "type": "string" },
        "commitment_type": { "type": "string", "const": "SHA512_QUANTUM_TELEPORTATION_BINDING" },
        "declared_at": { "type": "string", "format": "date-time" }
      }
    },
    "transmission_envelope": {
      "type": "object",
      "required": ["classical_channel_transport", "quantum_channel_profile", "freshness_window_seconds"],
      "properties": {
        "classical_channel_transport": { "type": "string", "const": "APPLICATION_LEVEL_CLASSICAL_TRANSMISSION" },
        "quantum_channel_profile": { "type": "string" },
        "freshness_window_seconds": { "type": "integer", "const": 300 }
      }
    }
  },
  "additionalProperties": false
}
```

---

## 5. Canonical Example Artifact

```json
{
  "format": "ZASLON-QDS",
  "version": "1.0.0",
  "project_id": "SIH-26141",
  "profile": "ZASLON-QDS-v1",
  "package_id": "8f3a1e2c-7b4d-4a1e-9f3c-2b5e8a7d1c3e",
  "session_id": "3c9b7e1a-4d2f-4b8a-9e1c-5f7a3b2d1e0f",
  "tracking_number": "QDS-20260917-8F3A1E2C",
  "document": {
    "filename": "Defense_Directive_2026.pdf",
    "file_size_bytes": 1048576,
    "mime_type": "application/pdf",
    "sha512_digest": "cf83e1357eefb8bdf1542850d66d8007d620e4050b5715dc83f4a921d36ce9ce47d0d13c5d85f2b0ff8318d2877eec2f63b931bd47417a81a538327af927da3e"
  },
  "cryptographic_binding": {
    "signer_identity": "alice",
    "designated_verifier": "bob",
    "declaration_hash": "a1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0",
    "nonce": "7c9e1b2a4d3f5e6a",
    "signed_at": "2026-09-17T18:30:00.000000Z"
  },
  "quantum_telemetry": {
    "quantum_run_id": "a5d8f1e2-9b3c-4e7a-8f1d-2c3e4b5a6d7e",
    "teleportation_operations_count": 4096,
    "cuda_q_target": "default",
    "principle_of_deferred_measurement": true
  },
  "public_declaration": {
    "declaration_id": "b7e2a1c4-3f5d-4a8e-9c1b-6e2d3a4b5c6d",
    "signature_token": "qds_tok_a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90",
    "commitment_type": "SHA512_QUANTUM_TELEPORTATION_BINDING",
    "declared_at": "2026-09-17T18:30:00.500000Z"
  },
  "transmission_envelope": {
    "classical_channel_transport": "APPLICATION_LEVEL_CLASSICAL_TRANSMISSION",
    "quantum_channel_profile": "Argonne SeQUeNCe 25km Standard Single-Mode Fiber (0.2 dB/km)",
    "freshness_window_seconds": 300
  }
}
```

---

## 6. Verification Consumption Flow

```text
       Alice Signs Payload
                │
                ▼
       Generates <filename>.qds.json
       (MySQL: is_consumed = False)
                │
                ▼
       Transmitted via Classical Channel
                │
                ▼
       Bob Receives in Inbox
                │
       ┌────────┴────────┐
       ▼                 ▼
[Runs 15-Check]     [Replay Attempt]
       │                 │
       ▼                 ▼
[Fisher p >= 0.01]  [is_consumed == True in DB]
       │                 │
       ▼                 ▼
Atomic Row-Lock    REJECTED (REPLAY)
Consumes Token:    (Token previously burned)
is_consumed = True
       │
       ▼
Generates .cert.json
```
