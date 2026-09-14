# ZASLON-QDS SIH26141 Audit and Docker Acceptance Report

Final validation date: 2026-09-13

## Executive result

The audited ZASLON-QDS application is running through Docker Compose on this
computer. The primary quantum worker executed CUDA-Q 0.15.1 on the NVIDIA target
with one visible NVIDIA GeForce RTX 4050 Laptop GPU. It did not use a CPU or
Qiskit fallback. The independent Qiskit Aer validation, SeQUeNCe network check,
full regression suite, live Alice-to-Bob flow, role isolation, and MySQL restart
persistence test all passed.

This is a genuine simulator-backed, teleportation-based QDS research application.
It is not a standardized QDS protocol, a physical quantum network, or a formal
information-theoretic security proof.

## A. Existing implementation found before modification

| Component | Initial classification | Finding |
| --- | --- | --- |
| SHA-512 document binding | COMPLETE | Exact uploaded bytes were already hashed and bound to the artifact. |
| Three-qubit teleportation | COMPLETE | The active CUDA-Q circuit already used message `q0`, Alice Bell half `q1`, and Bob Bell half `q2`. |
| Bell-state creation | COMPLETE | `H(q1)` and `CX(q1,q2)` were active. |
| Bell measurement | COMPLETE | `CX(q0,q1)`, `H(q0)`, and both measurements were active. |
| Pauli corrections | COMPLETE | The active convention was `m1 -> X` and `m0 -> Z`. |
| Z/X Pauli eigenstates | COMPLETE | Computational and phase-sensitive control states existed. |
| Projective measurements | COMPLETE | Active CUDA-Q kernels produced measurement outcomes. |
| CUDA-Q | COMPLETE | Real kernels, `cudaq.run`, and `cudaq.sample` were used; Python PRNG did not fabricate CUDA-Q outcomes. |
| Qiskit Aer | COMPLETE | It was an explicit independent validator, not a fallback. |
| SeQUeNCe | MISSING | No active distributed network layer existed. |
| Basis-aware statistics | COMPLETE | X/Z rates, Fisher tests, Holm correction, Wilson intervals, and classifier metrics existed. |
| Attack engine | COMPLETE | Baseline, intercept-resend, Pauli/Bell/correction manipulation, forgery, replay, and impersonation were in one active engine. |
| MySQL persistence | PARTIAL | MySQL worked, but startup DDL and the lack of a persistent worker queue required repair. |
| Role authorization | PARTIAL | API checks existed, but the browser-facing deployment needed server-side role proxies and route-family isolation. |

The existing scientific core was retained. No duplicate QDS, teleportation, or
attack implementation was introduced.

## B. Teleportation audit

The active circuit is:

```text
q0 = message qubit
q1 = Alice Bell-pair half
q2 = Bob Bell-pair half

prepare q0 as a Z- or X-basis eigenstate
H(q1)
CX(q1,q2)
CX(q0,q1)
H(q0)
m0 = MZ(q0)
m1 = MZ(q1)
if m1: X(q2)
if m0: Z(q2)
measure q2 in the requested basis
```

The stored classical-bit ordering is `(m0,m1)`:

| Bits | Correction |
| --- | --- |
| `00` | I |
| `01` | X |
| `10` | Z |
| `11` | X then Z, equivalent up to global phase to the reverse order |

All four outcomes are covered by regression tests. The direct CUDA-Q GPU test
recovered both computational-basis inputs in every ideal check. CUDA-Q target
validation uses sampled recovery and two-basis correlations rather than
fabricating statevector fidelity unavailable from the selected execution path.
Qiskit Aer independently reported Bell-state fidelity approximately 1.0 in the
validation run.

## C. Pauli and basis audit

- Z eigenstates `|0>` and `|1>` are supported.
- X eigenstates `|+>` and `|->` are supported.
- Y is supported as a manipulation, but Y-basis signing was not added merely to
  increase feature count.
- X, Y, and Z channel/output manipulations have declared circuit locations.
- Z-basis and X-basis statistics are separate.
- A Z phase operation on a Z eigenstate is correctly not claimed to cause a
  computational bit flip.
- A Z phase operation on an X eigenstate is observable by X-basis measurement.

Phase-sensitive control measurements strengthen manipulation detection, but they
do not constitute a proof of universal phase-attack detection.

## D. SeQUeNCe integration

SeQUeNCe was missing and was added once in the quantum worker. Version 0.7.6 is
pinned because it supports the NumPy 2.2.6 line required by the pinned CUDA-Q
image's CuPy installation. SeQUeNCe 1.0.0 requires NumPy 2.3.5 or newer and cannot
share this image with CuPy 13.4.1, which requires NumPy below 2.3.

The active bounded network adapter provides:

- Alice and Bob nodes, with optional Charlie for network experiments;
- directed quantum-channel metadata;
- Alice-to-Bob and Bob-to-Alice classical channels;
- propagation delay, attenuation/loss sampling, and delivered Bell-half counts;
- correction-message delivery and correction-integrity records;
- a network gate that must pass before CUDA-Q circuit work proceeds.

The separation is explicit:

```text
SeQUeNCe -> discrete-event delivery/control envelope
CUDA-Q   -> circuit, state preparation, teleportation, Pauli operations, measurement
```

The integration does not claim that a CUDA-Q statevector is physically shared
between containers or across the world.

## E. Statistics and decisions

Implemented measurements include overall mismatch/QBER, X-basis error rate,
Z-basis error rate, sample counts, teleportation agreement, timing, and engine
metadata. The detector uses one-sided Fisher exact tests where justified and Holm
family-wise correction across related tests. A p-value remains labelled a p-value.

The default 5% verification threshold is labelled
`CONFIGURED_EXPERIMENTAL`. It is not presented as a proven QDS bound. Forgery
trials report empirical success rates and Wilson intervals. Unsupported formal
forgery probability remains `RESEARCH_PENDING`.

## F. SIH requirement matrix

| SIH requirement | Status |
| --- | --- |
| Teleportation-based QDS | COMPLETE at simulator/research scope |
| Bell-state entanglement | COMPLETE at simulator scope |
| Quantum teleportation | COMPLETE |
| Pauli corrections | COMPLETE |
| Pauli eigenstates | COMPLETE for required X/Z states |
| Projective measurements | COMPLETE |
| Forgery detection | COMPLETE as empirical/deterministic testing |
| Impersonation | COMPLETE |
| Replay | COMPLETE |
| Unauthorized verification | COMPLETE |
| Channel manipulation | PARTIAL: circuit attacks complete; full network-stack adversaries remain future work |
| Statistical analysis | COMPLETE |
| Threshold decisions | COMPLETE with experimental provenance |
| Forgery probability analysis | RESEARCH_PENDING for a formal bound; empirical rate is implemented |
| Verification accuracy | COMPLETE as empirical evaluation |
| Performance metrics | COMPLETE for implemented execution paths |

## G. Code and deployment changes

Major files created or added to the supported runtime:

- `compose.yaml`
- `.dockerignore`
- `.env.example` and `.env.auth.example`
- `requirements-api.txt` and `requirements-worker.txt`
- `docker/api.Dockerfile`
- `docker/quantum-worker.Dockerfile`
- `docker/frontend.Dockerfile`
- `docker/nginx.conf.template`
- `docker/frontend-entrypoint.sh`
- `shared/backend/zaslon_shared/migrations.py`
- `shared/backend/zaslon_shared/migrate.py`
- `shared/backend/zaslon_shared/job_queue.py`
- `shared/backend/zaslon_shared/quantum_worker.py`
- `shared/backend/zaslon_shared/worker_health.py`
- `shared/backend/zaslon_shared/network.py`
- `shared/backend/zaslon_shared/secrets_init.py`
- `scripts/docker_acceptance.py`
- `IMPLEMENTATION_AUDIT.md`
- `START.md` and updated `walkthrough.md`

Major active modules modified include database models/configuration, dispatch,
FastAPI routes and health, Alice/Bob/Attack routers, Attack UI network controls,
Docker/security contract tests, queue tests, and temporary test database setup.

Database migrations:

1. `create_core_qds_schema`
2. `ensure_mysql_longtext_evidence`
3. `add_persistent_quantum_job_queue`
4. `widen_worker_engine_version`

No SQLite production database was introduced. SQLite is used only by isolated
automated tests in the container's temporary directory.

## H. Regression and acceptance evidence

| Validation | Result |
| --- | --- |
| Full backend/scientific/security suite | 82 passed, 1 skipped, 0 failed in 114.55 s |
| Focused repaired tests | 15 passed, 0 failed |
| CUDA-Q image dependency check | No broken requirements found |
| CUDA-Q target | `nvidia` |
| GPU | NVIDIA GeForce RTX 4050 Laptop GPU, one GPU visible |
| Known-state CUDA-Q kernel | PASSED |
| Bell diagnostic | PASSED |
| Four Bell-state classifications | PASSED |
| Broken/independent Bell negative controls | PASSED |
| Ideal teleportation checks | PASSED |
| Qiskit Aer cross-validation | PASSED; configured comparison tolerance satisfied |
| SeQUeNCe health | PASSED, version 0.7.6 |
| Alice live sign | PASSED on CUDA-Q `nvidia` |
| `.qds.json` generation/download | PASSED: `docker-acceptance.txt.qds.json` |
| Altered document rejection | PASSED: `INVALID` |
| Bob valid verification | PASSED: `VALID` |
| Attack Lab baseline | PASSED: `VALID` |
| AES-256-GCM decrypt round trip | PASSED |
| Browser role isolation | PASSED |
| MySQL restart persistence | PASSED; session remained retrievable after Compose down/up |
| Alice, Attack, Bob, and API host endpoints | HTTP 200 |

The persisted acceptance session is `QDS-20260913-EC63F2842D`.

## I. Honest remaining gaps

- `RESEARCH_PENDING`: a formal forgery-probability/security bound for this exact
  construction.
- `RESEARCH_PENDING`: a proof that the configured verification threshold is an
  optimal/protocol-secure bound.
- `EXPERIMENTAL`: the protocol is a discrete-qubit simulator-backed construction,
  not a standardized QDS scheme.
- `IMPLEMENTATION_PENDING`: full SeQUeNCe entanglement routing, repeater,
  purification, and quantum-memory lifecycle integration.
- `IMPLEMENTATION_PENDING`: production deployment beyond localhost requires TLS,
  identity-aware access control, managed secret storage/rotation, backups, and
  operational monitoring.
- `EXPERIMENTAL`: Bell correlations are diagnostics, not tomography or a
  device-independent Bell test.

## Docker deployment record

Long-running services:

- `frontend`: Node 22.22.0 Alpine build stage and nginx 1.29.1 Alpine runtime;
  publishes only `127.0.0.1:5173-5175`.
- `api`: Python 3.12.10 slim; publishes only `127.0.0.1:8000`; no CUDA-Q/GPU
  dependency.
- `quantum-worker`: NVIDIA NGC
  `nvcr.io/nvidia/quantum/cuda-quantum:cu12-0.15.1`; no published port; GPU
  passthrough enabled without privileged mode.
- `mysql`: official `mysql:9.7.2`; no published port.

One-shot services are `secrets-init` and `migrate`. They exit successfully after
their work and are not unnecessary always-running microservices.

Docker resources:

- private internal network: `zaslon-backend`;
- host-access edge network for API/frontend only: `zaslon-edge`;
- MySQL volume: `zaslon_mysql_data`;
- generated local secrets volume: `zaslon_local_secrets`.

Secrets are not baked into images or browser bundles. The initializer generates
separate database passwords, Alice/Bob/Attack role keys, and a Fernet job-payload
key. The application account is `zaslon_app`, not root. Worker job input is
encrypted at rest, claimed atomically, heartbeated, and cleared after completion.

Health gates are dependency-driven: secrets initialize, MySQL becomes healthy,
migrations complete, API and worker start, the worker executes known-state/Bell/
network checks, and the frontend starts after the API is healthy. No arbitrary
sleep is used for readiness.

CPU fallback, if explicitly enabled, remains CUDA-Q `qpp-cpu` and is reported.
Qiskit Aer is never a silent fallback.

The complete ZASLON-QDS development/runtime stack can be started through Docker
Compose without manually configuring or running the application inside a WSL
Ubuntu shell.

The supported command is:

```powershell
docker compose up -d --build
```

See `START.md` for the complete start, stop, health, validation, and recovery
commands.
