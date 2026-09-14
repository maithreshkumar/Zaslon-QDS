# ZASLON-QDS application walkthrough

## 1. Purpose and claim boundary

ZASLON-QDS is a teleportation-based Quantum Digital Signature research laboratory
for SIH26141. It executes Bell-pair preparation, three-qubit teleportation,
projective measurement, Pauli corrections, controlled attacks, verification, and
statistical detection. It does not use AI or machine learning.

This is not a standardized or information-theoretically proven QDS protocol. Its
configured mismatch threshold is labelled `CONFIGURED_EXPERIMENTAL`, not presented
as a security theorem. Empirical attack acceptance is not a proven forgery bound.

QDS provides experimental authenticity, integrity, and signer/verifier binding.
It does not encrypt a document. Optional payload confidentiality is a separate
AES-256-GCM mechanism with a scrypt-derived key.

## 2. Roles and privacy boundaries

- Alice signs documents for Bob and can verify documents signed by Bob.
- Bob signs documents for Alice, verifies Alice's artifacts, and can decrypt a
  separately authenticated confidentiality package.
- Attack runs controlled experiments against saved public/session state. It never
  receives Bob's or Alice's undisclosed measurement evidence.
- The trusted API enforces protocol, authorization, persistence, and one-time use.
- The quantum worker is the only normal runtime component that executes CUDA-Q.

Bob's user-facing inputs are the original document and `.qds.json` artifact. He
does not upload an attacker's experiment record. The backend independently checks
trusted session, nonce, history, and verifier evidence and reports validity and
supported attack findings.

Each role has a different server-side API key. Missing credentials return `401`;
cross-role access returns `403`. The browser bundle contains no role key. The
frontend's nginx proxy injects only the key for the requested role and denies
other role route families.

These keys model possession of an isolated laboratory participant computer. They
are not a substitute for user accounts, TLS, and managed identity on the public
internet.

## 3. Repository structure

```text
Alice/
  src/                         Alice React/TypeScript interface
  backend/alice_service/       Alice-specific router and service boundary

Attack/
  src/                         Attack Lab React/TypeScript interface
  backend/attacker_service/    attack-specific router and experiment modules

Bob/
  src/                         Bob React/TypeScript interface
  backend/bob_service/         Bob-specific router and service boundary

shared/backend/
  app/main.py                  composed trusted FastAPI gateway
  zaslon_shared/
    quantum.py                 CUDA-Q, Aer, and reference engine adapters
    qds.py                     active QDS protocol implementation
    attacks.py                 active attack experiment engine
    security.py                deterministic and statistical decisions
    db.py                      SQLAlchemy models
    migrations.py              versioned database migrations
    job_queue.py               encrypted persistent MySQL job queue
    quantum_worker.py          single quantum job executor
    worker_health.py           container health command
    network.py                 SeQUeNCe network experiment envelope

docker/
  api.Dockerfile               FastAPI/migration image
  quantum-worker.Dockerfile    NVIDIA CUDA-Q worker image
  frontend.Dockerfile          multi-stage Node/nginx image

compose.yaml                   complete Docker-first topology
START.md                       copy-paste startup and recovery guide
IMPLEMENTATION_AUDIT.md        pre-change requirement/runtime audit
```

Alice, Attack, and Bob have separate participant backend boundaries, but reuse the
shared scientific core. Duplicating the QDS or quantum implementation three times
would allow cryptographic rules and security fixes to drift.

## 4. Docker runtime architecture

```text
Windows 11
  -> Docker Desktop (WSL2 may be used internally)
       -> zaslon-frontend
       -> zaslon-api
       -> zaslon-quantum-worker
       -> zaslon-mysql + named volume
```

Normal traffic and work flow:

```text
browser
  -> role-restricted nginx path
  -> FastAPI authorization and validation
  -> encrypted MySQL quantum job
  -> single CUDA-Q/SeQUeNCe worker
  -> MySQL result
  -> API response
```

MySQL is not published to the host. The worker has no published port. All services
communicate using Docker service names over the private `zaslon-backend` network.
The API is deliberately CPU-only; GPU access belongs to the quantum worker.

The migration container waits for MySQL health, applies each schema version once,
and exits. API and worker start only after migrations succeed. Arbitrary sleep
delays and MySQL Workbench setup are not required.

## 5. Document and signing flow

1. The signer selects a document through Alice or Bob's interface.
2. The trusted API streams and bounds the upload, then computes SHA-512.
3. It submits an encrypted signing job to MySQL.
4. The single worker runs a SeQUeNCe delivery preflight when enabled.
5. CUDA-Q runs the Bell diagnostic and Bell-measurement stages using alternating
   Z/X Pauli eigenstates.
6. SeQUeNCe transports every actual Bell-result control used by the signing run.
7. Only after delivery, a CUDA-Q receiver-recovery kernel applies those controls
   and measures Bob's output. CUDA-Q 0.15 reconstructs the exact conditional
   receiver state across this run boundary; it does not claim persistent shared state.
8. Private verifier outcomes are persisted only in trusted storage.
9. Basis-aware public declarations, provenance, and a server HMAC attestation
   form the `.qds.json` artifact.
10. The signer interface downloads `<document-name>.qds.json` after success.
11. The stored public artifact remains downloadable by its authorized role.

For a 512-bit digest, two candidate values and four states per candidate produce
`512 × 2 × 4 = 4096` sequential transmissions. This means 4096 prepared states,
not 4096 simultaneous qubits. Each teleportation circuit has width three.

Raw uploaded documents are not placed in a permanent Docker volume. The database
stores the digest, signature metadata, trusted evidence, experiments, jobs, and
audit state—not a permanent copy of every uploaded file.

## 6. Teleportation physics

The standard qubit convention is:

```text
q0 = message qubit
q1 = Alice's Bell-pair half
q2 = Bob's Bell-pair half
```

The active circuit performs:

```text
prepare q0
H(q1)
CX(q1, q2)
CX(q0, q1)
H(q0)
m0 = measure q0
m1 = measure q1
if m1: X(q2)
if m0: Z(q2)
measure corrected q2 in the selected basis
```

The code retains both Bell bits. Its tested bit convention is:

| `(m0,m1)` | Bob correction |
| --- | --- |
| `00` | I |
| `01` | X |
| `10` | Z |
| `11` | XZ |

The engine records measured bits, tampered/used bits, required correction,
correction applied, and correction integrity. Attack code can therefore alter a
bit or correction without manufacturing an outcome.

Intercept-resend measures and re-prepares `q2`, the Bob-bound Bell half, after
Bell-pair creation and before Alice's Bell measurement. It never mislabels
Alice's local message qubit `q0` as a transmitted channel resource.

## 7. Bell-pair diagnostics and fidelity

Before production teleportation, fresh diagnostic copies of
`H(q1); CX(q1,q2)` are measured in Z and X. The diagnostic calculates `<ZZ>` and
`<XX>` and proceeds only when both meet the configured correlation threshold.
Those measured copies are never reused for teleportation.

This correlation witness is not full tomography, a loophole-free Bell test, or
proof that distant hardware shared entanglement. It checks the simulator's Bell
preparation independently from complete teleportation.

The reference and validation paths compute recovered-state fidelity where their
state representation supports it. The NVIDIA sampling path reports unavailable
statevector metrics instead of fabricating them. Measurement agreement and
basis-specific recovery statistics remain available.

## 8. Pauli eigenstates and projective measurements

The implemented protocol supports the states and bases it actually uses:

```text
Z basis: |0>, |1>
X basis: |+>, |->
```

Z-basis and X-basis measurement counts, errors, and rates are kept separate. This
is essential because a Z phase flip does not change a computational-basis bit:

```text
Z|0> = |0>
Z|1> = -|1>
```

It does swap X eigenstates and is observable in X measurement:

```text
Z|+> = |->
Z|-> = |+>
```

Tests forbid claiming complete phase-attack detection from Z-only evidence.
Y gates are implemented for the Pauli manipulation attack; a Y preparation basis
is not added merely to increase the feature count.

## 9. Quantum engine policy

### CUDA-Q

CUDA-Q is the primary computation engine. Its active `@cudaq.kernel` performs
state preparation, H/X/Y/Z, controlled-X, Bell processing, measurements,
measurement-dependent corrections, attack gates, and final measurement. Quantum
measurement outcomes do not come from Python's random module.

The worker uses the pinned image
`nvcr.io/nvidia/quantum/cuda-quantum:cu12-0.15.1` and normally requests the
`nvidia` target with `fp32`. Startup validates GPU visibility, target selection, a
known-state kernel, and Bell correlations. Health records the CUDA-Q version,
target, GPU count/name when available, and execution status.

Seeded classical randomness may select attacked positions, Eve's basis, and
experiment ordering. It does not fabricate state collapse or Bob's outcome.

An explicitly enabled CUDA-Q CPU fallback uses `qpp-cpu` and records why it was
used. No failure silently falls back to Qiskit Aer.

### Qiskit Aer

Qiskit Aer independently constructs and executes its own circuits. It is used by
tests and `/api/v1/validate/qiskit` for scientific cross-validation, not as a
continuously running service or hidden production fallback.

### NumPy reference engine

The explicit development engine evolves an eight-amplitude, three-qubit state
vector, performs actual projective collapse, applies corrections, and calculates
fidelity. It is a transparent test/debug option rather than disguised CUDA-Q.

## 10. SeQUeNCe network layer

SeQUeNCe 0.7.6 runs in the quantum-worker container. It models:

- Alice, Bob, and optional Charlie nodes;
- Alice→Bob and Alice→Charlie quantum channels for sampled Bell-half resource tokens;
- bidirectional Alice/Bob and Alice/Charlie classical channels;
- distance, attenuation/loss, propagation delay, and event timing;
- classical correction envelopes carrying every supplied CUDA-Q Bell bit in the signing run;
- network-level delivery/tampering observations.

CUDA-Q remains responsible for circuit/state physics. SeQUeNCe remains responsible
for network events. Placeholder random correction envelopes were removed. Health
uses a declared deterministic vector; production transports every actual CUDA-Q
`m0,m1` result before receiver recovery and records their hash. CUDA-Q 0.15
reconstructs the exact conditional receiver state in a second kernel because the
q2 allocation cannot survive while the Python SeQUeNCe event loop runs. It does
not claim that a statevector was physically shared across simulator processes.

Network metadata records nodes, channel counts, delivery attempts/successes,
delivery rate, correction-envelope integrity, simulated duration, and whether the
CUDA-Q gate opened. It contains no private verifier bases or outcomes.

## 11. Attack Lab

Implemented controlled experiments include:

- honest baseline;
- intercept-resend with Eve's projective measurement and re-preparation;
- output Pauli X, Y, and Z manipulation;
- Bell-pair-half manipulation;
- Bell measurement/correction-bit manipulation;
- correction-channel man-in-the-middle behavior;
- public-only signature forgery;
- replay of a consumed nonce;
- signer impersonation;
- unauthorized role-route access controls;
- bounded SeQUeNCe channel delivery/tampering experiments.

Attack strength is the independent selection probability for eligible states or
declarations. A seeded RNG makes selection reproducible, but attack outcomes are
derived from quantum execution and verification evidence.

The architecture exposes additional legitimate teleportation attack points for
future research without pretending they are all complete: Bell-pair substitution,
state replacement, broader entanglement degradation, and richer network routing.

## 12. Verification and replay safety

Verification checks:

- strict v2/v3 artifact schema and protocol version;
- HMAC-SHA512 trusted-server integrity and signer-role attestation for v3 artifacts;
- SHA-512 document binding;
- signer, verifier, session, and nonce binding;
- trusted private evidence retrieved independently from MySQL;
- correction and teleportation evidence;
- overall plus separate X/Z mismatch thresholds in the normal verification path;
- atomic one-time nonce consumption.

A valid signature can be consumed once. Concurrent reuse is rejected atomically.
Experiments operate on cloned/derived evidence and do not mutate trusted verifier
records or consume the real signature.

## 13. Statistics and decisions

Where applicable, results report:

- total and usable sample counts;
- overall mismatch/QBER;
- Z-basis measurements, errors, and error rate;
- X-basis measurements, errors, and error rate;
- teleportation agreement/fidelity when supported;
- timing and prepared-state/measurement counts;
- actual engine, target, and GPU/CPU status.

The blind detector compares attacked and saved honest control errors using a
one-sided Fisher exact test. Multiple related tests use Holm family-wise
correction. A p-value is reported as a p-value, never renamed “detection
confidence.” Results can be `ATTACK_DETECTED`, `NO_ATTACK_DETECTED`, or
`INCONCLUSIVE`.

Forgery trials report an empirical attack-success rate and Wilson interval. They
are labelled empirical. No unsupported formula is presented as a formal forgery
probability/security bound.

Repeated evaluation records valid signatures accepted, invalid signatures
rejected, honest signatures rejected, and attack signatures accepted so empirical
verification accuracy can be calculated without claiming a proof.

## 14. Persistence and queue recovery

MySQL 9.7.2 is authoritative. It uses a dedicated least-privilege application
account and a named Docker volume `zaslon_mysql_data`. `docker compose down` does
not erase it.

The API stores jobs rather than executing large circuits in its request process.
Job inputs are encrypted with Fernet before insertion. The single worker claims a
job using database locking, updates heartbeats during long work, stores the
result/error, and clears its encrypted input. A restarted worker recovers stale
claims according to the configured policy.

The database schema is migration-driven and versioned. It is not recreated on
every startup. SQLite appears only in isolated automated tests.

## 15. Security and input handling

- documents default to a 25 MiB limit and signatures to 5 MiB;
- empty and oversized uploads fail before scientific execution;
- artifact JSON is UTF-8 decoded, parsed safely, and validated by Pydantic;
- identifiers and download names are bounded/sanitized;
- SQLAlchemy uses parameter binding;
- role keys use constant-time comparisons;
- exported v3 signatures and stored attack records are server-attested with HMAC-SHA512;
- credentials remain in ignored `.env`/`.env.auth` files;
- database and worker ports are not exposed;
- containers drop Linux capabilities and do not use privileged mode;
- the Docker socket is never mounted;
- API/frontend filesystems are read-only except bounded tmpfs storage;
- cryptographic data and private measurement evidence never enter the browser
  artifact.

For any deployment beyond one local computer, use TLS and a real identity-aware
gateway. Do not expose the development Uvicorn or participant proxies directly to
the internet.

## 16. Frontend behavior

The three existing quantum-themed React interfaces are preserved:

- Alice: <http://127.0.0.1:5173/>
- Attack: <http://127.0.0.1:5174/>
- Bob: <http://127.0.0.1:5175/>

The redundant narrow navigation strip selected for removal is gone. Signing
downloads the public `.qds.json` artifact. Bob verifies from the document and that
artifact only and displays normal-path X/Z error rates. Each frontend obtains its
protocol version and online/degraded state from the live health endpoint. Attack
Lab labels SeQUeNCe delivery separately from CUDA-Q physics.

## 17. API overview

Important routes include:

```text
GET  /api/v1/health
GET  /api/v1/jobs/{job_id}

POST /api/v1/alice/sessions
POST /api/v1/alice/sign
POST /api/v1/alice/verify

POST /api/v1/bob/sign
POST /api/v1/bob/verify
POST /api/v1/bob/decrypt

GET  /api/v1/sessions
GET  /api/v1/sessions/{session_id}
GET  /api/v1/sessions/{session_id}/quantum-status
GET  /api/v1/sessions/{session_id}/signature

POST /api/v1/attacks/runs
GET  /api/v1/attacks/runs
POST /api/v1/attacks/network
GET  /api/v1/results/{experiment_id}

POST /api/v1/validate/qiskit
```

The API may return `202` with a job identifier when configured not to wait long
enough for a queued experiment. Job retrieval enforces the submitting role.

## 18. Starting, stopping, and testing

For a fresh local deployment, the one-shot initializer generates credentials in
the private `zaslon_local_secrets` volume. `.env` and `.env.auth` remain optional
templates for user-supplied overrides. Start with:

```powershell
docker compose up -d --build
```

Inspect health:

```powershell
docker compose ps
docker compose logs --tail 100 quantum-worker
```

Run tests:

```powershell
docker run --rm --gpus all --entrypoint pytest zaslon-qds-quantum-worker Attack/backend/tests shared/backend/tests -q -o cache_dir=/tmp/pytest-cache
docker compose exec quantum-worker python scripts/verify_cudaq.py
docker compose exec api python scripts/docker_acceptance.py
```

Stop without deleting data:

```powershell
docker compose down
```

Only `docker compose down -v` deletes the database volume; the application never
runs it automatically. Full setup, GPU preflight, troubleshooting, and recovery
commands are in [START.md](START.md).

## 19. Recommended experiment method

1. Create an honest, zero-noise baseline with a recorded seed.
2. Repeat across seeds and enough samples to show finite-sample variability.
3. Add calibrated normal noise and retain every parameter.
4. Run each attack across a declared strength range.
5. Report counts, Z/X errors, QBER, fidelity/accuracy where available, p-values,
   threshold provenance, engine, target, timing, and seed.
6. Cross-check representative circuits independently in Qiskit Aer.
7. Separate empirical findings from protocol-defined or research-derived claims.

## 20. Honest remaining limitations

- This is simulator-backed; it does not control a physical quantum network.
- The construction is a research protocol, not a standardized QDS scheme.
- The 5% default threshold requires experiment-specific calibration.
- SeQUeNCe causally transports actual CUDA-Q classical correction bits before
  receiver recovery and models resource-delivery tokens, but it does not preserve a shared
  cross-simulator quantum state or implement a full quantum-memory/repeater lifecycle.
- The Bell witness is not tomography or a device-independent Bell test.
- Formal forgery probability/security bounds remain research pending.
- Public-network deployment still requires TLS, managed identities, secret
  rotation, and production key management.
- GPU success must be demonstrated inside the actual worker container on each
  deployment; a successful source-level or WSL test is not Docker proof.
