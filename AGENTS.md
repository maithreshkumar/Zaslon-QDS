# Zaslon-QDS — Permanent Agent Operating Rules & Architecture Guidelines

## 0. Permanent Agent Operating Rule: Plan First

For every substantial software-development task:
1. **Inspect and analyze** the current codebase before modifying code.
2. **Produce an explicit implementation plan** and detailed task checklist.
3. **Identify affected modules, dependencies, and risks**.
4. **Implement incrementally** in logical phases.
5. **Validate each major phase** with real unit, integration, and syntax tests.
6. **Finish with a completion report** containing build results, test outputs, and decision records.

---

## 1. Core Architectural & Scientific Invariants

1. **Quantum Foundation**:
   - Strictly based on **3-Qubit Quantum Teleportation** ($Q_0$: Message/State, $Q_1$: Alice's Bell Qubit, $Q_2$: Bob's Bell Qubit).
   - Real circuit execution on **NVIDIA CUDA-Q** (`cudaq` PyPI package).
   - Never mock quantum results with `random.choice`, `numpy.random`, or static returns.
   - If CUDA-Q runtime is unavailable, return an explicit `CUDA_Q_UNAVAILABLE` error.

2. **Cryptographic Binding**:
   - Canonical hashing uses standard `SHA-512` (`hashlib.sha512`).
   - Deterministic expansion maps the 512-bit digest to 4,096 teleportation operation states ($\theta_k, \phi_k$) and bases ($Z$ or $X$).
   - Public declarations bind session ID, message digest, signer identity, and cryptographic commitment tokens.

3. **Statistical Verification & Hypotheses**:
   - Sample-based verification selects ~5% of operations ($N_{\text{sample}} \approx 205$) deterministically using a session-bound seed.
   - Fisher's Exact Test (`scipy.stats.fisher_exact`) evaluates observed match/mismatch contingency data against the theoretical authentic quantum channel error baseline.
   - Experimental parameters (`MISMATCH_THRESHOLD_RATIO`, `FISHER_SIGNIFICANCE_ALPHA`, `BASELINE_ERROR_RATE`, `REPLAY_WINDOW_SECONDS`) are configurable and documented as security policy parameters.

4. **Threat Detection & Simulation**:
   - Detects 5 primary threat classes: **Forgery**, **Impersonation**, **Replay**, **Unauthorized Verification**, and **Integrity Tampering**.
   - Attack simulations genuinely manipulate underlying inputs, identities, declarations, or quantum states in the test environment, and pass through the identical, authentic detection pipeline.

5. **Decision & Explainability Standards**:
   - Strictly **NO AI / ML** components.
   - Decisions are deterministic, transparent, and mathematically derived.
   - Clearly distinguish: `VALID` vs `INVALID`, `VERIFIED` vs `REJECTED`, `AUTHORIZED` vs `UNAUTHORIZED`, `NO ATTACK DETECTED` vs `ATTACK DETECTED`, `INTEGRITY VALID` vs `INTEGRITY FAILURE`, `STATISTICALLY ACCEPTABLE` vs `STATISTICALLY SUSPICIOUS`.
