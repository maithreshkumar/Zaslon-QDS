# ZASLON-QDS Implementation Audit Before Docker Migration

Audit date: 2026-09-12

This document records the runtime trace and gap classification before the
Docker-first/network-worker implementation. It distinguishes active code from
compatibility wrappers and UI labels. It is not a formal QDS security proof.

## Active runtime path

```text
Alice/Bob/Attack React clients
  -> localhost role proxy
  -> FastAPI app.main
  -> role router
  -> zaslon_shared.protocol or zaslon_shared.attacks
  -> zaslon_shared.quantum.CudaQEngine
  -> CUDA-Q kernel execution
  -> SQLAlchemy session
  -> MySQL (configured production database)
```

`shared/backend/zaslon_shared/*` contains the active implementation. The
`shared/backend/quantum_network`, `shared/backend/protocol`, and participant
helper modules are thin compatibility/import facades. They are not independent
QDS or quantum engines and must not be duplicated.

## Requirement audit

| Requirement | Exists? | Classification | Runtime used? | Evidence and action |
|---|---:|---|---:|---|
| SHA-512 | Yes | COMPLETE | Yes | `sha512_hex(document)` binds the exact uploaded bytes. Keep. |
| Bell-pair creation | Yes | COMPLETE | Yes | Active CUDA-Q kernel executes `H(q1)` and controlled-X `q1 -> q2`. Keep. |
| 3-qubit teleportation | Yes | COMPLETE | Yes | CUDA-Q allocates `qvector(3)` with message `q0`, Alice Bell half `q1`, Bob half `q2`. Keep. |
| Bell measurement | Yes | COMPLETE | Yes | Active kernel executes `CX(q0,q1)`, `H(q0)`, then measures `q0` and `q1`. Keep. |
| Classical correction bits | Yes | COMPLETE | Yes | Both outcomes are returned as `(m0,m1)` and stored per state. Keep; add network transport records. |
| Pauli X correction | Yes | COMPLETE | Yes | `m1` controls X on Bob's `q2`. Keep. |
| Pauli Z correction | Yes | COMPLETE | Yes | `m0` controls Z on Bob's `q2`. Keep. |
| Pauli eigenstates | Yes | COMPLETE | Yes | Z (`|0>`,`|1>`) and X (`|+>`,`|->`) preparation are implemented. Y is intentionally not a protocol basis. |
| X-basis projective measurement | Yes | COMPLETE | Yes | H basis rotation followed by CUDA-Q `mz`; used by fresh channel diagnostics. Keep. |
| Z-basis projective measurement | Yes | COMPLETE | Yes | CUDA-Q `mz`; used by production declarations and diagnostics. Keep. |
| Phase-sensitive verification | Yes | PARTIAL | Yes | Fresh independent X-basis channel controls detect phase disturbance, but the production artifact remains computational-basis-only. Preserve the honest claim boundary. |
| CUDA-Q execution | Yes | COMPLETE | Yes | Real `@cudaq.kernel`, `cudaq.run`, and `cudaq.sample`; target metadata is recorded and missing CUDA-Q fails closed. Keep. |
| Qiskit Aer validation | Yes | COMPLETE | On demand/tests | Independent engine comparison; not a runtime fallback. Keep. |
| SeQUeNCe network model | No | MISSING | No | Add one network layer in the quantum worker; do not replace CUDA-Q. |
| Quantum channel | Circuit-level only | PARTIAL | Yes | Noise/attacks have declared quantum boundaries, but no distributed network timing/loss model exists. Connect SeQUeNCe. |
| Classical channel | Logical only | PARTIAL | Yes | Correction-bit MITM is modeled logically, but no channel delay/topology is simulated. Connect SeQUeNCe. |
| Entanglement distribution | Local simulation only | PARTIAL | Yes | Bell resources are created and diagnosed, but not distributed through network nodes/channels. Add SeQUeNCe metadata and delivery/loss experiment. |
| Attack engine | Yes | COMPLETE | Yes | One active engine covers baseline, intercept-resend, Pauli/entanglement manipulation, Bell-result/correction tampering, forgery, replay, and impersonation. Keep. |
| Statistical detector | Yes | COMPLETE | Yes | Basis-aware rates, Fisher tests, Holm correction, Wilson intervals, classifier metrics, and constrained calibration exist. Keep. |
| Forgery | Yes | COMPLETE | Yes | Partial tampering and independent full forgery are separate. Empirical rates and restricted reference calculation are correctly labelled. Keep. |
| Replay | Yes | COMPLETE | Yes | One-time nonce and atomic conditional database consumption reject concurrent replay. Keep. |
| Impersonation | Yes | COMPLETE | Yes | Authenticated role/participant binding rejects signer substitution. Keep. |
| Unauthorized verification | Yes | COMPLETE | Yes | Intended verifier is checked against the authenticated server-side role. Keep. |
| Channel manipulation | Yes | PARTIAL | Yes | CUDA-Q supports intercept-resend and X/Y/Z plus Bell/correction manipulation; network loss/delay attack points are missing. Add only network layer support. |
| Teleportation fidelity | Yes | PARTIAL | Yes | Reference engine calculates pure-state fidelity; CUDA-Q sampling target reports recovery/error statistics and does not fabricate inaccessible statevectors. Keep. |
| Threshold provenance | Yes | COMPLETE | Yes | Default is `CONFIGURED_EXPERIMENTAL` and explicitly not a proven bound. Keep. |
| Verification accuracy | Yes | COMPLETE | Benchmark path | TP/TN/FP/FN and derived empirical rates exist. Keep. |
| Performance metrics | Yes | COMPLETE | Yes | Signing, verification, attack runtime, sequential state count, measurements, target, GPU flag, and maximum circuit width are reported. Extend with queue/network timing. |
| MySQL persistence | Yes | PARTIAL | Yes | MySQL is supported and used as system of record, but tables are created/altered at app startup and no persistent job queue exists. Add idempotent migrations and queue. |
| Browser/private evidence separation | Yes | COMPLETE | Yes | Browser artifacts omit Bob/Charlie private evidence; role secrets remain server-side. Keep. |

## Teleportation and correction convention

The active CUDA-Q circuit is physically equivalent to the standard protocol:

```text
q0: message qubit
q1: Alice Bell-pair half
q2: Bob Bell-pair half

H(q1)
CX(q1,q2)
CX(q0,q1)
H(q0)
m0 = MZ(q0)
m1 = MZ(q1)
if m1: X(q2)
if m0: Z(q2)
```

The stored tuple is `(m0,m1)`. The resulting correction convention is:

| `(m0,m1)` | Bob correction |
|---|---|
| `00` | I |
| `01` | X |
| `10` | Z |
| `11` | X then Z (equivalent up to global phase to Z then X) |

The existing regression tests force/observe all four Bell outcomes and verify
recovery. This implementation must not be rebuilt.

## Randomness audit

Classical seeded PRNG use is limited to experiment selection, input labels,
noise-event selection, and independent reference-engine Born sampling. CUDA-Q
measurement outcomes originate from CUDA-Q kernels. Qiskit outcomes originate
from Aer. Nonces use `secrets`.

## Scientific gap report

### Keep unchanged

- Active three-qubit CUDA-Q teleportation and Bell diagnostics.
- X/Z eigenstate preparation and projective measurement.
- Pauli corrections and exact bit ordering.
- Strict `.qds.json` validation and public/private evidence separation.
- Attack engine, phase-sensitive diagnostic, statistics, replay, identity, and
  authorization controls.
- Qiskit Aer as explicit independent validation only.

### Repair or complete

- Replace startup DDL with a versioned, idempotent migration runner.
- Move quantum/signing/attack execution out of the API process.
- Persist job lifecycle in MySQL and make worker claims restart-safe.
- Add queue and network timing to performance records.
- Replace manual WSL startup as the primary supported deployment.

### Implement once

- Docker Compose with frontend, API, CUDA-Q/SeQUeNCe worker, migration, and
  MySQL 9.7 services.
- SeQUeNCe 0.7.6 network adapter for Alice, Bob, optional Charlie, quantum and
  classical channels, delay/loss, and declared network attack points.
- Worker health separating process, CUDA-Q, and GPU status.
- A single frontend image serving the three existing built interfaces on their
  existing ports and proxying each role without exposing keys to JavaScript.

### Remain research-limited

- The production signature construction is a discrete computational-basis
  research protocol, not a standardized/formally proven QDS scheme.
- X-basis controls support phase-disturbance detection but are not a proof of
  universal phase-attack detection.
- SeQUeNCe simulates network behavior; it does not create physical long-distance
  entanglement.
- Forgery probability is empirical or a restricted reference model unless its
  assumptions are independently justified.

## Docker migration baseline gaps

| Docker requirement | Pre-migration status | Required action |
|---|---|---|
| Compose entrypoint | MISSING | Add `compose.yaml`. |
| Frontend container | MISSING | Multi-stage build of existing Alice/Attack/Bob apps. |
| API container | MISSING | CPU-only API image; no CUDA-Q dependency or GPU access. |
| Quantum worker | MISSING | NVIDIA CUDA-Q 0.15.1 image plus worker and SeQUeNCe. |
| MySQL 9.7 container | MISSING | Pin official `mysql:9.7.2`, internal-only, named volume. |
| Persistent queue | MISSING | Add MySQL `quantum_jobs` table and atomic claim/recovery. |
| Migrations | MISSING | Add migration service and schema version ledger. |
| Health checks | PARTIAL | API health exists; add container, worker, migration, and frontend checks. |
| GPU validation | PARTIAL | Host/WSL CUDA-Q validated; add in-container known-state worker health. |
| Secret-safe configuration | PARTIAL | Existing server-side keys are sound; adapt to Compose secrets/env without baking values. |
| Restart persistence | PARTIAL | QDS rows persist in MySQL; add job recovery and verify named-volume restart. |

## Pre-implementation decision

Proceed by adapting the active shared implementation. Do not create a second QDS
engine, attack engine, or quantum circuit implementation. The only new major
runtime components are the MySQL job boundary, SeQUeNCe network adapter,
migrations, and Docker packaging.
