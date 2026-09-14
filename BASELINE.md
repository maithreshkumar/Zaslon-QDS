# ZASLON-QDS hardening baseline

Recorded: 2026-08-31 (Asia/Calcutta), before the scientific-hardening changes.

## Environment

| Environment | Value |
|---|---|
| WSL Python | 3.12.3 |
| Windows test Python | 3.14.3 |
| CUDA-Q | 0.15.1 (`aca5853`) |
| CUDA-Q target | `nvidia`, FP32, 1 GPU, no fallback |
| Qiskit / Aer | 2.5.2 / 0.17.2 |
| WSL NumPy | 2.5.2 |
| Windows NumPy / SciPy | 2.4.6 / 1.18.1 |
| FastAPI / SQLAlchemy | 0.141.1 / 2.0.43 |
| Node | 26.7.0 |

The user-level Windows `npm` launcher was broken at baseline because its global
`npm-cli.js` path did not exist. The explicit system npm launcher remained the
known working build path.

## Existing suite

`31 passed, 1 skipped` in 64.56 seconds. The skip was the Windows-host CUDA-Q
availability case; CUDA-Q was independently exercised in WSL on the GPU.

## Isolated reference-engine baseline

Input: `phase-zero-baseline`, seed `20260831`, zero configured noise.

| Measurement | Result |
|---|---:|
| Signature generation | 2.0654 s |
| Verification | 0.0148 s |
| Teleportations / Bell pairs consumed sequentially | 4096 |
| Maximum simultaneous circuit width | 3 qubits |
| Disclosed measurements | 2048 |
| Honest mismatches / QBER | 0 / 0.0 |
| Mean state fidelity | 1.0 |

Bell diagnostic used 2048 fresh Z copies and 2048 fresh X copies. Counts were
Z: `00=1028, 11=1020`; X: `00=1039, 11=1009`; both correlations were 1.0.

## Existing attack behavior

| Experiment | Runtime | Mismatch rate | Detector | Verification |
|---|---:|---:|---|---|
| Baseline | 0.0217 s | 0.0 | No attack detected | VALID |
| Intercept-resend, 100% | 0.8730 s | 0.23096 | Detected | INVALID |
| Output Pauli Z, 100% | 1.1572 s | 0.0 | Not detected | VALID |
| Bell-result manipulation, 100% | 0.8559 s | 0.66797 | Detected | INVALID |

The Pauli-Z result records the confirmed production Z-basis phase-sensitivity
gap. The reported Fisher p-values were respectively 1.0, approximately
`1.57e-156`, 1.0, and 0.0; at baseline the API did not adjust them for a family
of repeated tests.

## CUDA-Q Bell baseline

CUDA-Q on the `nvidia` target used 256 shots per basis: Z `00=109, 11=147`, X
`00=123, 11=133`, with `<ZZ>=1.0`, `<XX>=1.0`, classification `PHI_PLUS`, and
no fallback. Direct state metrics were unavailable on this sampling target and
were correctly left null.
