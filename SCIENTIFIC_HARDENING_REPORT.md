# ZASLON-QDS Scientific Hardening Report

Updated from the implementation and reproducible validation on 2026-09-13. Raw
measured data is in
[FINAL_VALIDATION_RESULTS.json](FINAL_VALIDATION_RESULTS.json) and
[CUDA_VALIDATION_RESULTS.json](CUDA_VALIDATION_RESULTS.json).

## A. Changes made

| Problem | Main files | Implementation | Verification |
|---|---|---|---|
| Teleportation regressions could be hidden | `quantum.py`, `test_teleportation_regression.py` | Preserved q0/q1/q2 ordering, Bell measurement, m1→X and m0→Z correction | All four Bell outcomes and X/Y/Z disturbance tests pass |
| Malformed or partial artifacts could reach statistical verification | `schemas.py`, `protocol.py` | Strict Pydantic schema, exact 512-position validation, canonical order, digest/key/session/nonce/identity binding, no coercion or unknown fields | Negative artifact, mixing, and mutation tests pass |
| Browser-controlled identities | Alice/Bob routers, `auth.py` | Signer and verifier derive from authenticated server role | Spoofed signer and unauthorized verifier tests pass |
| Replay race | `protocol.py` | Atomic conditional `UPDATE ... WHERE consumed_at IS NULL` | Concurrent test accepts exactly one request |
| Z-only evidence misses phase changes | `quantum.py`, `protocol.py`, `attacks.py` | Production v3 signatures alternate X/Z states; independent controls remain separate | Pure Z attack leaves production Z error at zero, flips X evidence, and is rejected |
| Network bits were post-hoc | `quantum.py`, `network.py`, `protocol.py` | Staged Bell measurement → SeQUeNCe delivery → receiver recovery; private delivery receipts are removed before persistence | Causal delivered-bit regression and Docker acceptance cover the active path |
| Calibration reused evaluation data | `benchmark.py` | Domain-separated calibration and held-out datasets with separately declared noise profiles | Held-out confusion metrics are emitted independently of threshold selection |
| Forgery copied a legitimate signature | `attacks.py` | Kept partial tampering separately; full forger constructs every field/declaration independently and copies zero legitimate declaration key bits | Independent full forgery and partial tampering tests pass |
| Inconsistent noise | `quantum.py` | One composed Pauli order across NumPy, Aer, CUDA-Q; Bell-distribution, output/memory, and measurement locations are distinct | Three-engine combined-noise result matches exactly in final 256+256-shot run |
| Ideal Bell diagnostic overstated channel quality | `quantum.py`, `protocol.py` | Separate `IDEAL_SOURCE_PREPARATION` and `EFFECTIVE_BELL_DISTRIBUTION` diagnostics | Ideal/noisy diagnostic tests pass |
| Attack boundaries were ambiguous | `attacks.py`, `adversary.py`, `SECURITY_MODEL.md` | Explicit counterfactual semantics, adversary capabilities, and distinct Bell-result/correction-MITM bit traces | Attack matrix and boundary tests pass |
| Statistical labels and repeated tests | `security_analysis.py`, `benchmark.py` | Fisher tests, Holm family-wise correction, Wilson intervals, classifier metrics, constrained calibration | Statistical semantics/calibration tests pass |
| No transferability experiment | `multiverifier.py` | One bundle with independent Bob/Charlie evidence, authenticated forwarding, experimental `s_a < s_v` | Honest and selective-disturbance trials pass |
| CUDA-Q global state/concurrency | `quantum.py`, `runtime.py` | Target initialized at controlled startup, execution and seeding serialized, health never configures engine | Real WSL/NVIDIA two-thread test passes |
| Resource exhaustion | `runtime.py`, role routers, schemas | Nonblocking bounded quantum-job slot; bounded files, shots, repetitions, strengths, and forgery trials | 429/Retry-After and schema-bound tests pass |
| Browser role secrets | `proxy.py`, three `proxy_app.py` files, React clients | Local role proxies inject server-side keys; browser code sends none | Production bundle scan found zero header names or live keys |
| Secret/archive risk | `auth.py`, `.gitignore`, `create_source_archive.py` | Template rejection and strict source allowlist excluding env files, DBs, builds, caches, venvs | Archive allowlist test passes |
| Unpinned dependencies | `requirements.txt`, workspace `package.json`, `package-lock.json` | Exact tested Python/Node versions | Backend tests and all three production builds pass |
| Hidden metrics | React Alice/Bob/Attack views | Exposes engine, Bell pairs, max qubits, ideal/effective Bell results, mismatch/QBER, p-values, intervals, FPR/FNR, transferability, repudiation, and runtime | TypeScript and Vite production builds pass |

## B. Original known-issue status

1. Formal forgery bound — **IMPROVED BUT NOT FORMALLY SOLVED**. A restricted IID
   binomial calculation exists, but final output labels it `REFERENCE BOUND` because
   the IID/fixed-attacker-error assumptions are not established.
2. Non-repudiation — **IMPROVED BUT NOT FORMALLY SOLVED**. Recipient-selective
   Bob-accepts/Charlie-rejects behavior is measured, not proven impossible.
3. Transferability — **IMPROVED BUT NOT FORMALLY SOLVED**. Bob and Charlie use
   independent evidence and authenticated forwarding; no standard-QDS proof applies.
4. Empirical threshold — **IMPROVED BUT NOT FORMALLY SOLVED**. Calibration is
   traceable and FPR-constrained, but remains simulation-specific.
5. Signer identity binding — **FIXED**.
6. Intended-verifier binding — **FIXED**.
7. Structural validation — **FIXED**.
8. Phase-only blind spot — **FIXED FOR NORMAL V3 EVIDENCE AND THE Z/X CHANNEL DIAGNOSTIC**; this
   does not turn the entire scheme into a proven QDS construction.
9. Atomic replay — **FIXED**.
10. Nonstandard/incomplete formal QDS construction — **STILL OPEN**. It is correctly
    presented as a discrete-qubit research simulation.

## C. Newly discovered issue status

1. Copy-based forgery — **FIXED**.
2. CUDA-Q combined-noise replacement — **FIXED**.
3. Noise applied only after correction — **FIXED** with named locations.
4. Bell diagnostic ignored noise — **FIXED** with separate effective diagnostic.
5. Post-measurement attack language — **FIXED**; results say counterfactual execution.
6. Bell-result and correction MITM conflation — **FIXED AT THE TRUST/AUDIT BOUNDARY**;
   equivalent final Pauli effects are disclosed.
7. Related randomness streams — **FIXED for implemented simulation paths** with
   SHA-256 domain-derived deterministic streams; nonces still use `secrets`.
8. No multiple-test correction — **FIXED** with Holm FWER for Z/X families.
9. Misleading “statistically consistent” wording — **FIXED**; now
   `within_configured_tolerance` and explicitly not an equivalence test.
10. CUDA-Q global target/seed mutation — **FIXED** with controlled initialization and lock.
11. Missing admission control — **FIXED**.
12. Browser credentials — **FIXED**; bundle scan is clean.
13. Archive secret risk — **FIXED FOR ARCHIVES CREATED BY THE PROVIDED ALLOWLIST TOOL**.
14. Weak test names/assertions — **FIXED/EXPANDED** with property-specific tests.
15. Missing frontend metrics — **FIXED for the implemented backend metrics**.

## D. Quantum correctness

- Bell resource: `H(q1)` then `CX(q1,q2)`, with fresh pairs and separate diagnostic copies.
- Teleportation: message q0, Alice half q1, Bob half q2; Bell outcomes cover 00/01/10/11.
- Correction: second Bell bit controls X; first controls Z.
- Measurement: projective Born-rule sampling with collapse/normalization in the reference engine.
- Bases: production v3 declarations alternate Z and X; fresh diagnostics independently use Z and X.
- Maximum simultaneous circuit width: three qubits.
- Final combined-noise validation (256 shots per basis): all three engines measured
  Z error `0.2578125`, X error `0.23046875`, combined QBER `0.244140625`.
- CUDA-Q result: target `nvidia`, GPU true, fallback false.

## E. Mathematical correctness

The implementation uses these equations/decisions:

1. Document digest: SHA-512 over the exact uploaded byte sequence.
2. QBER/mismatch rate: `e / n`, using usable measurements as the denominator.
3. Bell correlations: `(N00 + N11 - N01 - N10) / N` in Z and X.
4. Pure-state fidelity: `|<psi_input|psi_output>|²`; mixed effective diagnostics do
   not report pure-state concurrence/entropy.
5. Wilson 95% interval for empirical binomial proportions.
6. One-sided Fisher exact test for an observed error increase against an independent
   honest run.
7. Holm FWER adjustment: ordered raw p-values are multiplied by the number of
   remaining hypotheses and monotonically adjusted.
8. TPR=`TP/(TP+FN)`, TNR=`TN/(TN+FP)`, FPR=`FP/(FP+TN)`, FNR=`FN/(FN+TP)`,
   precision=`TP/(TP+FP)`, and balanced accuracy=`(TPR+TNR)/2`.
9. Restricted reference forgery model: `X ~ Binomial(L,p_e)` and
   `P_accept=P[X<=floor(tL)]`. It is not a ZASLON security guarantee unless IID and
   fixed justified `p_e` assumptions are established.

## F. Statistical correctness and measured results

- Detector records are separated into independently seeded `CALIBRATION` and
  `HELD_OUT_EVALUATION` datasets. Threshold selection uses calibration records only.
- The current final validation uses ten repetitions per scenario/strength/dataset,
  64 shots per basis and independently seeded samples under a predeclared nonzero
  operating-noise profile.
- Per-attack/per-strength power curves, held-out confusion metrics, Wilson intervals,
  false-positive rate and honest-abort rate are retained in the raw JSON. Weak attacks
  are not described as universally detectable.
- Full independent forgery uses 128 bounded trials; empirical acceptance and its
  Wilson interval are retained in the raw JSON.
- Reference binomial value: `1.50627142141528e-112` for L=512, p_e=0.5,
  threshold=0.05/cutoff=25, explicitly **not formally applicable**.
- Honest and selective-disturbance multi-verifier experiments use ten bounded trials;
  exact outcomes and Wilson intervals are retained in the raw JSON.
  This exposes a limitation; it is not proof of non-repudiation.
- A p-value is never presented as an attack probability or posterior confidence.

## G. QDS security status

| Property | Status | Evidence |
|---|---|---|
| Unforgeability | **PARTIAL** | Fail-closed trusted binding and empirical independent-forger rejection; no universal proof |
| Non-repudiation | **PARTIAL** | Experimental selective-recipient measurement; unfavorable case remains possible |
| Transferability | **EMPIRICALLY SUPPORTED** | Independent Bob/Charlie evidence and honest trials; small sample and no proof |
| Robustness | **EMPIRICALLY SUPPORTED** | Honest/noise/strength sweeps and confidence intervals |
| Replay resistance | **FORMALLY SUPPORTED AT THE IMPLEMENTATION/DB TRANSACTION LEVEL** | Atomic conditional consume and concurrency test |
| Signer authentication | **FORMALLY SUPPORTED AT THE IMPLEMENTED ROLE BOUNDARY** | Server-derived role identity and negative tests |
| Verifier authorization | **FORMALLY SUPPORTED AT THE IMPLEMENTED ROLE/SESSION BOUNDARY** | Authenticated verifier equals stored intended verifier |

## H. Scientifically safe statements for SIH judges

- “ZASLON-QDS genuinely executes a discrete three-qubit teleportation circuit in
  CUDA-Q and independently compares distributions with Qiskit Aer and NumPy.”
- “The simulator uses fresh Bell pairs sequentially; 4096 pairs consumed does not
  mean 8192 entangled qubits coexist.”
- “Production signature evidence is separate from fresh randomized Z/X channel
  controls, so a pure phase operation becomes observable in the X basis.”
- “Attack decisions use projective measurements, deterministic protocol validation,
  Fisher tests, and Holm correction—no AI or machine learning.”
- “Forgery, transferability, repudiation, and detector rates shown here are empirical
  under explicitly documented adversary and noise models.”
- “The displayed binomial forgery value is a restricted reference comparison, not a
  proof for the whole implementation.”

## I. Claims that must not be made

- Do not call ZASLON-QDS information-theoretically secure or formally proven secure.
- Do not claim this is a standardized complete QDS protocol.
- Do not claim the 2023 continuous-variable teleportation-QDS paper proves this
  discrete-qubit construction.
- Do not call an absolute-tolerance comparison statistical equivalence.
- Do not call a p-value the probability of an attack.
- Do not claim the configured/calibrated threshold transfers to physical hardware
  without new calibration.
- Do not claim simulated shared state is a deployed long-distance quantum network.

## J. Performance results

Current latency, throughput and engine timings are generated into
`FINAL_VALIDATION_RESULTS.json` and `CUDA_VALIDATION_RESULTS.json`; this narrative
does not duplicate mutable measurements. Production Bell pairs are consumed
sequentially and maximum circuit width remains three qubits. Memory/GPU-utilization
distributions remain unmeasured and are never fabricated.

## K. Test results

- Latest pre-staging complete backend suite: **80 passed, 6 environment-specific skips**.
- Current focused post-staging suite: **26 passed** before the final complete rerun.
- Container-only SeQUeNCe/CUDA-Q paths are validated in the Docker worker.
- All Alice, Attack, and Bob TypeScript/Vite production builds pass.
- Production browser scan: zero `VITE_ZASLON_API_KEY`, credential-header, or live-key matches.

## L. Remaining issues

1. No complete security reduction for unforgeability, non-repudiation, or transferability.
2. Multi-verifier support is an experimental recipient-specific bundle, not a standard
   symmetrized QDS implementation.
3. The current 5% production threshold is still configuration; final reference
   calibration selected 0 only because the honest simulator was ideal.
4. Physical devices, loss, detector efficiency, side channels, and quantum memories
   are not modeled completely.
5. The root workspace intentionally still contains ignored local `.env`, `.env.auth`,
   and database/runtime files. Use `scripts/create_source_archive.py`; do not zip the
   folder manually.
6. Rotate role credentials before an external demonstration if any prior copy may
   have been shared.
7. Ten multi-verifier trials still leave broad uncertainty; publication-quality
   work needs substantially larger preregistered experiments.

## M. Final verdict

**SIH READY — WITH DOCUMENTED LIMITATIONS**

The implementation is credible for an SIH research demonstration: the teleportation
core, cross-engine noise behavior, fail-closed verification, authorization, replay,
phase-sensitive diagnostics, statistical semantics, concurrency controls, and browser
credential boundary are concretely tested. It is not “SIH READY — STRONG” in the
formal-cryptographic sense because a complete QDS security proof and standard
non-repudiation/transferability construction remain open.
