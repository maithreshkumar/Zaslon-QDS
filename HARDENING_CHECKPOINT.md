# ZASLON-QDS hardening checkpoint

Safe stop recorded: 2026-08-31 (Asia/Calcutta).

## Completed and verified

- Baseline inventory and [BASELINE.md](BASELINE.md).
- Teleportation regression protection.
- Strict fail-closed signature artifact validation.
- Trusted signer identity and intended-verifier enforcement.
- Atomic one-time signature consumption under concurrent verification.
- Dedicated Z/X control-state channel diagnostics, separate from production evidence.
- Canonical composed Pauli noise semantics across NumPy, Qiskit Aer, and CUDA-Q.
- Actual CUDA-Q/NVIDIA combined-noise comparison in WSL.
- Separate partial-tampering and independent full-forgery experiments.
- Domain-separated simulation randomness for the paths changed so far.
- Explicit adversary model in [SECURITY_MODEL.md](SECURITY_MODEL.md).
- Holm correction, classifier metrics, threshold-calibration utility, and restricted
  binomial reference-bound utility.
- Distinct audit boundaries for Bell-result manipulation and correction-channel MITM.
- Ideal Bell-source and effective Bell-distribution diagnostics implemented.

## Last verified test results

- P0 complete backend suite: `53 passed, 2 skipped` in 107.12 seconds.
- Actual WSL CUDA-Q/NVIDIA combined-noise test: `1 passed` in 11.31 seconds.
- Most recent focused Bell/noise checkpoint after effective-channel changes:
  `15 passed, 1 skipped` in 8.98 seconds.

The focused skip is expected on native Windows because CUDA-Q runs in the configured
WSL/Linux environment. No installer, server, test, or background command was left
running by this checkpoint.

## Completion update (2026-09-01)

The requested implementation pass continued from this checkpoint. P1/P2 hardening,
frontend metric exposure, final three-engine validation, and the final scientific
report are now complete. See `SCIENTIFIC_HARDENING_REPORT.md`,
`FINAL_VALIDATION_RESULTS.json`, and `CUDA_VALIDATION_RESULTS.json`.

## Historical resume point

Continue P1 at effective Bell-diagnostic integration review, then implement and test:

1. Multi-verifier/Charlie experimental flow, transferability, and repudiation metrics.
2. Reproducible detector benchmark and empirical threshold-calibration harness.
3. Empirical/reference forgery analysis surfaced in experiment results.
4. Full P1 regression suite.

After P1, proceed to the pending P2 work: CUDA-Q process-global concurrency safety,
admission control, non-mutating health checks, server-side browser credential proxies,
secret/archive safety, pinned dependencies, frontend metric exposure, documentation,
and the final reproducible experiment matrix.

## Important claim boundary

The project is not yet complete under the attached hardening specification. Do not
claim formal information-theoretic QDS security. Current transferability and
non-repudiation remain unfinished at this checkpoint.
