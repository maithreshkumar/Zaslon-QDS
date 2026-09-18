# QDS Workflow Specification — Zaslon-QDS

Quantum-Teleportation-Based Quantum Digital Signature Workflow for SIH 26141.

---

## 1. Protocol Pipeline Overview

The complete signature lifecycle proceeds through 6 sequential, deterministic stages:

```text
Plaintext Message (M)
       ↓
[Stage 1: Cryptographic Hashing]
       ↓ SHA-512
512-Bit Digest (D)
       ↓
[Stage 2: Deterministic State Mapping]
       ↓ 4,096 Rotations & Bases
Quantum State Parameters {θ_k, φ_k, b_k, basis_k}
       ↓
[Stage 3: 3-Qubit Quantum Teleportation]
       ↓ NVIDIA CUDA-Q Engine
Bob's Reconstructed States & Raw Measurements
       ↓
[Stage 4: Public Declaration]
       ↓ Cryptographic Commitment
Signed Declaration Token (S_id, H(D), Token)
       ↓
[Stage 5: Deterministic Verification Sampling]
       ↓ 5% Sample Selection (Seed: S_id ⊕ D)
Observed vs Expected Mismatch Computation
       ↓
[Stage 6: Statistical & Cybersecurity Decision Engine]
       ↓ Fisher's Exact Test + RBAC + Replay Rules
Final Explainable Verdict (VERIFIED / REJECTED)
```

---

## 2. Stage-by-Stage Specifications

### Stage 1: Cryptographic Hashing
- Algorithm: Standard `SHA-512` (FIPS 180-4).
- Input: Arbitrary plaintext or binary message $M$.
- Output: 64-byte hex digest (512 bits) $D = \text{SHA-512}(M)$.
- Tamper Verification: During verification, $M$ is re-hashed to guarantee that $D_{\text{recomputed}} = D$.

### Stage 2: Deterministic State Mapping
- Total operations: Configured via `TELEPORTATION_COUNT=4096`.
- Expansion: The 512-bit digest is expanded into 4,096 bit/basis pairs via deterministic PRF rounds.
- Qubit $Q_0$ rotation:
  - $Z$-basis:
    - Bit 0: $|\psi\rangle = |0\rangle$ ($\theta = 0, \phi = 0$).
    - Bit 1: $|\psi\rangle = |1\rangle$ ($\theta = \pi, \phi = 0$).
  - $X$-basis:
    - Bit 0: $|\psi\rangle = |+\rangle$ ($\theta = \pi/2, \phi = 0$).
    - Bit 1: $|\psi\rangle = |-\rangle$ ($\theta = \pi/2, \phi = \pi$).

### Stage 3: 3-Qubit Quantum Teleportation (CUDA-Q)
- Each operation executes on CUDA-Q with 3 allocated qubits:
  - $Q_0$: Alice's message state.
  - $Q_1$: Alice's Bell pair qubit.
  - $Q_2$: Bob's Bell pair qubit.
- Alice performs Bell-basis measurement on $(Q_0, Q_1)$ yielding classical bits $(m_0, m_1)$.
- Bob applies conditional feed-forward Pauli corrections: $X^{m_1} Z^{m_0}$ on $Q_2$.
- Bob measures $Q_2$ in the corresponding basis ($Z$ or $X$).
- Execution is batched (default 512 ops/batch) for throughput and responsiveness.

### Stage 4: Public Declaration
- Signer (Alice) publishes the declaration to the ledger/database.
- Contains:
  - `session_id`
  - `signer_id`
  - `signature_token`: Cryptographically secure high-entropy token.
  - `declaration_payload_hash`: SHA-512 commitment over session metadata and quantum run outcomes.
  - `declared_at`: High-precision timestamp.

### Stage 5: Deterministic Verification Sampling
- Configurable ratio: `VERIFICATION_SAMPLE_RATIO=0.05` (~205 operations sampled from 4,096).
- Reproducibility: Sample indices are deterministically derived using pseudo-random sampling seeded by `hash(session_id + total_count + sample_ratio)`.
- For each sampled index $i$, the engine evaluates:
  - $\text{Expected Bit}_i$ vs $\text{Observed Bit}_i$.
  - Evaluates match flag: $\text{Match}_i = (\text{Expected Bit}_i == \text{Observed Bit}_i)$.

### Stage 6: Statistical & Cybersecurity Decision Engine
- Constructs $2 \times 2$ contingency table comparing observed matches/mismatches against the theoretical quantum channel baseline error limit (1%).
- Evaluates exact one-sided Fisher Exact Test $p$-value (`scipy.stats.fisher_exact`).
- Security thresholds:
  - $\alpha = 0.01$ (significance level).
  - Maximum mismatch tolerance: $\tau = 3\%$.
- Concurrently evaluates participant role authorization, replay token freshness, and hash integrity.
- Outputs explainable decision verdict (`VERIFIED`, `REJECTED`, `UNAUTHORIZED`, `INTEGRITY_FAILURE`).
