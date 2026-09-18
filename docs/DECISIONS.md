# Zaslon-QDS Architectural & Engineering Decision Records (ADR)

## Context & Objectives
This document maintains formal engineering decision records for the Zaslon-QDS platform (SIH 26141: Quantum-Teleportation-Based Cyber Threat Detection for Quantum Digital Signatures).

---

### ADR-001: Migration to Official `cudaq` PyPI Package
- **Status**: Implemented & Verified
- **Context**: During container configuration, the package `cuda-quantum` was identified as deprecated on PyPI by NVIDIA in favor of `cudaq` (version 0.16.0+).
- **Decision**: Updated `quantum/requirements.txt` to require `cudaq>=0.16.0`.
- **Consequences**: Enables official pre-built Linux wheels (`cuda_quantum_cu13-0.16.0`) with CUDA 13 runtime support, high-performance CPU emulation, and GPU acceleration.

---

### ADR-002: Principle of Deferred Measurement for 3-Qubit Quantum Teleportation
- **Status**: Implemented & Mathematically Verified
- **Context**: CUDA-Q 0.16.0 enforces strict constraints on mid-circuit branching: `cudaq.sample` no longer permits classical `if m:` conditions on mid-circuit measurement results.
- **Decision**: Applied the Principle of Deferred Measurement (Nielsen & Chuang, *Quantum Computation and Quantum Information*, §4.4):
  $$\text{Classical Feed-Forward } (X^{m_1} Z^{m_0}) \iff \text{Quantum Operations } CX(q_1, q_2) \cdot CZ(q_0, q_2)$$
  Controlled-$Z$ is implemented via the canonical identity $H \cdot CX(q_0, q_2) \cdot H$. Bob's basis selection (computational $Z$ vs. Hadamard $X$) applies $H$ when designated. All three qubits are measured simultaneously at the circuit termination.
- **Consequences**:
  - $100\%$ mathematical equivalence to classical feed-forward teleportation.
  - Zero mid-circuit classical branching overhead.
  - Full compatibility with `cudaq.sample` across all simulation targets.
  - Verified with $100\%$ fidelity on $|0\rangle, |1\rangle, |+\rangle, |-\rangle$ basis states.

---

### ADR-003: Deterministic Fisher's Exact Test & Safe JSON Serialization
- **Status**: Implemented & Verified
- **Context**: In an ideal or near-ideal quantum channel, the sample mismatch count is $0$. Under a $2 \times 2$ contingency table with a zero cell, `scipy.stats.fisher_exact` yields an odds ratio of $\infty$. Direct floating-point serialization of $\infty$ violates the JSON standard (RFC 8259) and causes API serializer failures.
- **Decision**: Handled zero-mismatch conditions by formatting the odds ratio into `safe_odds_ratio` (`null` in JSON) and `odds_ratio_display` (`"Infinity"` string), while computing the exact one-sided $p$-value ($p \ge \alpha$). Configurable parameters (`BASELINE_ERROR_RATE`, `FISHER_SIGNIFICANCE_ALPHA`, `MISMATCH_THRESHOLD_RATIO`) are injected dynamically with descriptive mathematical reasoning.
- **Consequences**: Clean API serialization, mathematically exact hypothesis evaluation, and deterministic explainability.

---

### ADR-004: Asynchronous Batched Quantum Execution & Live Progress Tracking
- **Status**: Implemented & Verified
- **Context**: Teleporting 4,096 operations generates substantial circuit execution and database insertion volume. Synchronous HTTP execution risks client-side timeouts.
- **Decision**:
  - Structured `TeleportationService` to support both synchronous execution (for automated testing) and asynchronous background tasks via FastAPI `BackgroundTasks`.
  - Added database columns: `completed_operations`, `failed_operations`, `current_batch`, and `total_batches`.
  - Added dedicated endpoint `GET /api/v1/sessions/{session_id}/quantum-status` for live frontend progress polling.
- **Consequences**: Scalable non-blocking execution with real-time UI visibility.

---

### ADR-005: Atomic Single-Use Token Consumption & Replay Barriers
- **Status**: Implemented & Verified
- **Context**: QDS security requires that a public declaration and its quantum signature token cannot be intercepted and replayed in subsequent verification requests.
- **Decision**:
  - Enhanced `PublicDeclarationModel` with `is_consumed`, `consumed_at`, and `consumed_in_verification_id`.
  - Upon successful verification (`VERIFIED`), `DeclarationService.consume_declaration()` atomically marks the token as consumed.
  - Any subsequent verification attempt using the same declaration is rejected with `ThreatCategories.REPLAY`.
  - Added timestamp freshness validation enforcing `REPLAY_WINDOW_SECONDS`.
- **Consequences**: Strict prevention of replay attacks and cryptographic cross-session isolation.

---

### ADR-006: Multi-Signal Explainable Threat Detection Engine
- **Status**: Implemented & Verified
- **Context**: The platform must detect 5 distinct cyber threat classes without relying on probabilistic or opaque machine learning models.
- **Decision**: Implemented a multi-signal deterministic decision engine in `VerificationService`:
  1. **Unauthorized Verification**: Verifier ID $\ne$ designated `session.verifier_id`.
  2. **Signer Impersonation**: Declaration signer $\ne$ session designated signer.
  3. **Replay Attack**: Consumed declaration token reuse or expiration of freshness window.
  4. **Integrity Tampering**: SHA-512 recomputed digest $\ne$ recorded digest.
  5. **Quantum Forgery**: Sample mismatch ratio $> \tau$ and Fisher exact test $p < \alpha$.
- **Consequences**: Transparent, verifiable, deterministic cybersecurity verdicts meeting SIH 26141 requirements.
