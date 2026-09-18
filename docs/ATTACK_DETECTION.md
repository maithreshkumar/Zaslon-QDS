# Cyber Attack Detection & Threat Demonstration — Zaslon-QDS

Specification of the 5 Threat Classes, Detection Mechanics, and Controlled Simulation for SIH 26141.

---

## 1. Threat Classes Overview

Zaslon-QDS detects and demonstrates at least 5 major cyber threat classes against Quantum Digital Signatures:

| Threat Class | Attack Surface | Physical / Cryptographic Consequence | Detection Mechanism | Security Decision |
| :--- | :--- | :--- | :--- | :--- |
| **FORGERY** | Quantum state / measurements | Measurement basis discrepancies, state disturbance | 5% Sample Mismatch Ratio > 3%, Fisher Exact Test ($p < 0.01$) | `REJECTED` |
| **IMPERSONATION** | Participant identity | Spoofed public key fingerprint or unregistered actor token | Backend RBAC check against session participant table | `UNAUTHORIZED` |
| **REPLAY** | Public declaration token | Stale signature reuse across sessions or timestamps outside window | Unique token constraint validation & freshness check ($\Delta t > 300\text{s}$) | `REJECTED` |
| **UNAUTHORIZED_VERIFICATION** | Verification endpoint | Non-verifier calling `/verify` | Backend verifier authorization check (`actor == session.verifier_id`) | `UNAUTHORIZED` |
| **INTEGRITY_TAMPERING** | Message / Declaration payload | Text payload altered after SHA-512 computation | Cryptographic hash recalculation mismatch ($\text{SHA-512}(M) \ne D_{\text{stored}}$) | `INTEGRITY_FAILURE` |

---

## 2. Deep Dive: Detection Logic

### A. Forgery Detection (Quantum Level)
In a quantum digital signature scheme, forging a signature requires measuring or generating states without knowledge of Alice's preparation basis. Due to the No-Cloning Theorem, any eavesdropper (Eve) or malicious party measuring in the conjugate basis introduces a minimum error rate of 25% to 50% into Bob's measurements.
When ~5% of operations are sampled, an authentic run yields $\approx 0\%$ mismatch. A forged run exhibits an elevated mismatch ratio:
$$\text{Mismatch Ratio} = \frac{\text{Mismatches}}{\text{Sample Size}} > 0.03$$
The Fisher Exact Test yields an infinitesimally small $p$-value ($p \ll 0.01$), mathematically proving the occurrence of state forgery.

### B. Impersonation Detection (Identity Level)
Every session registers authorized participants (`Signer`, `Verifier`, `Administrator`) with unique cryptographic public key fingerprints. Direct API calls with forged or missing credentials are intercepted by `AuthorizationService` before state transitions are allowed.

### C. Replay Detection (Protocol Level)
Every public declaration generates a single-use high-entropy cryptographic nonce token (`sig_qds_...`). A declaration can only be consumed once. Furthermore, declarations carry an immutable UTC timestamp; tokens presented outside the replay window ($\Delta t > 300\text{s}$) or already consumed are flagged with `REPLAY_DETECTED`.

### D. Unauthorized Verification (Access Control Level)
Only the designated verifier registered during session initialization (`session.verifier_id`) is authorized to execute the verification sampling and statistical evaluation. Calls from any other actor are immediately denied with HTTP 403 and logged in the audit trail.

### E. Integrity Tampering (Message Level)
Before sampling begins, the verifier recomputes $\text{SHA-512}(\text{raw\_message})$ and compares it against the digest committed during session initialization. Any byte alteration in the plaintext results in an entirely divergent SHA-512 hash, immediately terminating the verification with `INTEGRITY_FAILURE`.

---

## 3. Controlled Simulation Architecture

In compliance with project specifications, attack simulation **never returns fake pre-baked JSON responses**. Instead, the simulation service:
1. Genuinely modifies the database record (e.g., bit-flips 300 measurement outcomes, modifies message text, or passes an unauthorized actor).
2. Directs the modified session data through the **standard, authentic verification pipeline**.
3. The standard pipeline evaluates the data, detects the inconsistency, generates verifiable evidence, logs the audit event, and returns the explainable decision.
