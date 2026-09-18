# Zaslon-QDS — Canonical 13-Attack Threat Catalog
## SIH 26141 — Quantum-Teleportation-Based Cyber Threat Detection for QDS

---

## 1. Attack Taxonomy Overview

Zaslon-QDS systematically catalogs and defends against **13 canonical cyber and quantum threat vectors** categorized into 4 physical/logical families. Each vector exercises genuine physical mutations in the test environment and is evaluated against Bob's 15-check verification engine without heuristic fallbacks or mock quantum returns.

---

## 2. Attack Family 1: Identity & Authorization Attacks

### Vector 1: Signer Identity Impersonation (`IMPERSONATION`)
- **Target Layer**: Protocol / Identity Binding (Classical Channel)
- **Eve Adversary Action**: Intercepts in-flight package and mutates the declared signer identity from `"alice"` to an adversarial identity (`"Eve_Impersonator"`).
- **Physical Mutation**: `declaration.signer_id = "Eve_Impersonator"`, `package.sender_id = "Eve_Impersonator"`.
- **Bob Verification Check**: Check 06 (`Signer Identity Binding Check`).
- **Triggered Barrier**: Barrier 2: Signer Identity Binding Barrier.
- **Expected Decision**: `REJECTED (IMPERSONATION)`.
- **Audit / Event**: `SECURITY_EVENT: IMPERSONATION_DETECTED`, `AUDIT_EVENT: VERIFICATION_REJECTED`.

### Vector 2: Unauthorized Verification Attempt (`UNAUTHORIZED_VERIFICATION`)
- **Target Layer**: Access & Role-Based Authorization (Classical API)
- **Eve Adversary Action**: Eve attempts to execute Bob's verification endpoint (`POST /inbox/{id}/verify`) using adversary credentials.
- **Physical Mutation**: None (Direct unprivileged invocation of Bob's verification pipeline).
- **Bob Verification Check**: Check 02 (`Verifier Authorization Barrier`).
- **Triggered Barrier**: Barrier 1: Verifier Authorization Barrier.
- **Expected Decision**: `UNAUTHORIZED` (HTTP 403 Forbidden).
- **Audit / Event**: `SECURITY_EVENT: UNAUTHORIZED_VERIFICATION`, `AUDIT_EVENT: ACCESS_DENIED`.

### Vector 3: Unauthorized Verifier Resource Probe (`UNAUTHORIZED_PROBE`)
- **Target Layer**: System Access / Private Verifier Telemetry
- **Eve Adversary Action**: Eve attempts to probe Bob-private endpoints (`GET /verification/{id}/samples` or Bob's inbox) to discover the private 5% sample indices before delivery.
- **Physical Mutation**: None (Direct unprivileged probe against Bob-private telemetry).
- **Bob Verification Check**: Check 02 (Resource Policy & RBAC Guard).
- **Triggered Barrier**: Barrier 1: RBAC Verifier Policy Barrier.
- **Expected Decision**: `UNAUTHORIZED` (HTTP 403 Forbidden).
- **Audit / Event**: `SECURITY_EVENT: UNAUTHORIZED_PROBE` (Visible in Bob's "Alerts" tab).

---

## 3. Attack Family 2: Artifact & Integrity Attacks

### Vector 4: File Integrity Tampering (`FILE_INTEGRITY_TAMPERING`)
- **Target Layer**: Classical Document Artifact (`payload.bin`)
- **Eve Adversary Action**: Modifies document bytes on disk or in payload after Alice computed and locked the SHA-512 digest.
- **Physical Mutation**: Appends `b"\n[TAMPERED_BY_EVE]"` or alters bytes in `payload.bin`.
- **Bob Verification Check**: Check 07 (`Streaming SHA-512 File Recomputation Integrity`).
- **Triggered Barrier**: Barrier 4: Cryptographic SHA-512 File Integrity Barrier.
- **Expected Decision**: `INTEGRITY_FAILURE`.
- **Audit / Event**: `AUDIT_EVENT: HASH_MISMATCH`, `AUDIT_EVENT: VERIFICATION_REJECTED`.

### Vector 5: Public Declaration Tampering (`DECLARATION_TAMPERING`)
- **Target Layer**: Manifest Metadata (`.qds.json`)
- **Eve Adversary Action**: Modifies the public declaration commitment parameters or hash inside `<filename>.qds.json`.
- **Physical Mutation**: `declaration.declaration_payload_hash = compute_sha512(b"TAMPERED_DECLARATION")`.
- **Bob Verification Check**: Check 08 (`Declaration Commitment Integrity`).
- **Triggered Barrier**: Barrier 3: Public Declaration Commitment Integrity Barrier.
- **Expected Decision**: `INTEGRITY_FAILURE`.
- **Audit / Event**: `AUDIT_EVENT: DECLARATION_TAMPERING`, `AUDIT_EVENT: VERIFICATION_REJECTED`.

### Vector 6: QDS Package Manifest Tampering (`QDS_PACKAGE_TAMPERING`)
- **Target Layer**: Classical Transmission Envelope (`qds_packages`)
- **Eve Adversary Action**: Forges the committed SHA-512 digest inside the package manifest to mask document tampering.
- **Physical Mutation**: `package.committed_digest = compute_sha512(b"FORGED_DOCUMENT_DIGEST")`.
- **Bob Verification Check**: Check 04 (`Package Integrity & Canonical Manifest Commitment`).
- **Triggered Barrier**: Barrier 4: Cryptographic SHA-512 File Integrity Barrier.
- **Expected Decision**: `INTEGRITY_FAILURE`.
- **Audit / Event**: `AUDIT_EVENT: PACKAGE_INTEGRITY_FAILURE`.

### Vector 7: Quantum Bit-Flip Forgery (`FORGERY`)
- **Target Layer**: Cryptographic Binding & Quantum Telemetry
- **Eve Adversary Action**: Synthesizes a forged signature token and perturbs quantum states without authentic entanglement correlation.
- **Physical Mutation**: Replaces signature token with synthesized token; flips Bob's observed measurement bits ($Q_2 \to \neg Q_2$) across 600 operations.
- **Bob Verification Check**: Check 13 & 14 (`Sample Mismatch Barrier` & `Fisher's Exact Test`).
- **Triggered Barrier**: Barrier 5: Quantum Teleportation Fisher Exact Test Barrier.
- **Expected Decision**: `REJECTED (FORGERY)`.
- **Audit / Event**: `ATTACK_EVENT: FORGERY_DETECTED`, `AUDIT_EVENT: VERIFICATION_REJECTED`.

---

## 4. Attack Family 3: Protocol Attacks

### Vector 8: Single-Use Token Replay (`REPLAY`)
- **Target Layer**: Protocol State & Temporal Freshness
- **Eve Adversary Action**: Captures a previously verified, valid package and resubmits it, or delays transmission beyond 300s.
- **Physical Mutation**: Replays token where database `is_consumed == True`, or backdates timestamp by 600 seconds.
- **Bob Verification Check**: Check 09 (`Server-Authoritative Anti-Replay & Freshness Window`).
- **Triggered Barrier**: Barrier 3: Anti-Replay Single-Use Token Barrier.
- **Expected Decision**: `REJECTED (REPLAY)`.
- **Audit / Event**: `SECURITY_EVENT: REPLAY_ATTACK_DETECTED`.

### Vector 9: Quantum Intercept-and-Resend (`INTERCEPT_AND_RESEND`)
- **Target Layer**: Simulated Quantum Channel / Network Fiber Link
- **Eve Adversary Action**: Intercepts in-transit Bell photons, measures in arbitrary bases, and transmits newly reconstructed states to Bob.
- **Physical Mutation**: Simulates non-orthogonal projective measurement collapse, inducing $\sim 50\%$ mismatch across 650 sample operations.
- **Bob Verification Check**: Check 13 & 14 (`Sample Mismatch Ratio` & `Fisher's Exact Test`).
- **Triggered Barrier**: Barrier 5: Quantum Teleportation Fisher Exact Test Barrier.
- **Expected Decision**: `REJECTED`.
- **Audit / Event**: `ATTACK_EVENT: INTERCEPT_AND_RESEND_DETECTED`.

### Vector 10: Cross-Session Token Substitution (`SESSION_SUBSTITUTION`)
- **Target Layer**: Cryptographic Cross-Binding
- **Eve Adversary Action**: Grafts a public declaration token from an unrelated QDS session into the current package envelope.
- **Physical Mutation**: `package.signature_token = f"sig_qds_foreign_{uuid.uuid4().hex}"`.
- **Bob Verification Check**: Check 05 (`Session & Cryptographic Binding Check`).
- **Triggered Barrier**: Barrier 3: Cross-Session Cryptographic Binding Barrier.
- **Expected Decision**: `REJECTED` / `INTEGRITY_FAILURE`.
- **Audit / Event**: `AUDIT_EVENT: CROSS_SESSION_BINDING_MISMATCH`.

---

## 5. Attack Family 4: Quantum Evidence Attacks

### Vector 11: Measurement Bit Manipulation (`MEASUREMENT_MANIPULATION`)
- **Target Layer**: Quantum Measurement Evidence (`teleportation_operations`)
- **Eve Adversary Action**: Directly flips Bob's observed teleportation bits ($0 \leftrightarrow 1$) on teleported qubits via active Pauli-X perturbation.
- **Physical Mutation**: Inverts `bob_observed_bit = 1 - expected_bit` for 600 operations in the database.
- **Bob Verification Check**: Check 13 & 14 (`Sample Mismatch Barrier` & `Fisher's Exact Test`).
- **Triggered Barrier**: Barrier 5: Quantum Teleportation Fisher Exact Test Barrier ($p < 0.01$).
- **Expected Decision**: `REJECTED (FORGERY)`.
- **Audit / Event**: `ATTACK_EVENT: MEASUREMENT_MANIPULATION`.

### Vector 12: Conjugate Basis Manipulation (`BASIS_MANIPULATION`)
- **Target Layer**: Quantum Basis Assignment Metadata
- **Eve Adversary Action**: Forces Bob to measure in orthogonal conjugate bases ($Z \leftrightarrow X$) by manipulating basis flags in the quantum stream.
- **Physical Mutation**: Inverts state preparation angles ($\theta \to \pi - \theta$) and basis flags across 600 operations, producing $\approx 50\%$ random errors.
- **Bob Verification Check**: Check 13 & 14 (`Sample Mismatch Barrier` & `Fisher's Exact Test`).
- **Triggered Barrier**: Barrier 5: Quantum Teleportation Fisher Exact Test Barrier ($p < 0.01$).
- **Expected Decision**: `REJECTED (FORGERY)`.
- **Audit / Event**: `ATTACK_EVENT: BASIS_MANIPULATION`.

### Vector 13: Quantum State Replacement & Phase Depolarization (`QUANTUM_STATE_REPLACEMENT`)
- **Target Layer**: Quantum State Coherence / Fiber Channel Profile
- **Eve Adversary Action**: Injects phase-damping noise (Pauli-Z) and depolarizing decoherence, disrupting deferred measurement feed-forward parity.
- **Physical Mutation**: Inverts $Z$-corrections (`bob_correction_z = 1 - bob_correction_z`) across 800 operations.
- **Bob Verification Check**: Check 13 & 14 (`Sample Mismatch Barrier` & `Fisher's Exact Test`).
- **Triggered Barrier**: Barrier 5: Quantum Teleportation Fisher Exact Test Barrier ($p < 0.01$).
- **Expected Decision**: `REJECTED (FORGERY)`.
- **Audit / Event**: `ATTACK_EVENT: QUANTUM_STATE_REPLACEMENT`.

---

## 6. Comprehensive Attack & Detection Matrix

| # | Family | Attack Name | Target Channel | Eve Physical Action | Triggered Barrier | Expected Verdict |
| :- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | Identity | **Impersonation** | Classical | Mutates `signer_id` in declaration & envelope | Barrier 2: Signer Identity Binding | `REJECTED` (`IMPERSONATION`) |
| **2** | Identity | **Unauthorized Verification** | Classical | Eve invokes Bob verify endpoint directly | Barrier 1: Verifier Authorization | `UNAUTHORIZED` (HTTP 403) |
| **3** | Identity | **Unauthorized Probe** | System | Eve attempts to read `/verification/{id}/samples` | Barrier 1: RBAC Verifier Policy | `UNAUTHORIZED` (HTTP 403) |
| **4** | Artifact | **File Integrity Tampering** | Classical | Injects byte tampering into `payload.bin` | Barrier 4: SHA-512 File Integrity | `INTEGRITY_FAILURE` |
| **5** | Artifact | **Declaration Tampering** | Classical | Alters declaration commitment hash | Barrier 3: Declaration Commitment | `INTEGRITY_FAILURE` |
| **6** | Artifact | **QDS Package Tampering** | Classical | Alters declared digest in manifest | Barrier 4: SHA-512 File Integrity | `INTEGRITY_FAILURE` |
| **7** | Artifact | **Forgery** | Both | Synthesizes fake token & flips quantum bits | Barrier 5: Fisher Exact Test | `REJECTED` (`FORGERY`) |
| **8** | Protocol | **Replay** | Classical | Resubmits consumed token or backdates time | Barrier 3: Anti-Replay Single-Use | `REJECTED` (`REPLAY`) |
| **9** | Protocol | **Intercept-and-Resend** | Quantum | Intercepts & reconstructs Bell qubits | Barrier 5: Fisher Exact Test | `REJECTED` |
| **10**| Protocol | **Session Substitution** | Classical | Grafts foreign session token into package | Barrier 3: Cross-Session Binding | `REJECTED` / `INTEGRITY_FAILURE` |
| **11**| Quantum  | **Measurement Manipulation** | Quantum | Pauli-X bit flip ($0 \leftrightarrow 1$) on Bob bits | Barrier 5: Fisher Exact Test | `REJECTED` (`FORGERY`) |
| **12**| Quantum  | **Basis Manipulation** | Quantum | Basis alteration ($Z \leftrightarrow X$) | Barrier 5: Fisher Exact Test | `REJECTED` (`FORGERY`) |
| **13**| Quantum  | **Quantum State Replacement** | Quantum | Pauli-Z phase flip & depolarizing noise | Barrier 5: Fisher Exact Test | `REJECTED` (`FORGERY`) |
