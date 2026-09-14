# ZASLON-QDS

ZASLON-QDS is a local, three-node Quantum Digital Signature research laboratory. Alice and Bob can both sign and verify documents. The Attack node runs controlled channel, protocol, identity, replay, and forgery experiments against saved sessions.

The application distinguishes three different concerns:

- QDS provides experimental authenticity, integrity, and signer/verifier binding.
- AES-256-GCM provides optional payload confidentiality. QDS itself is not encryption.
- Attack detection compares independent honest/attacked Z/X control-state errors
  using one-sided Fisher exact tests and Holm family-wise correction. Deterministic
  identity, artifact, and replay rules are reported separately.

The active protocol is a teleportation-based research QDS construction. Alice encodes signature evidence as computational-basis message qubits, the engine teleports each message through a Bell pair, and Bob measures the corrected output. It is not a standardized QDS scheme and the configured threshold is not a proven security bound.

## Project layout

```text
Alice/                 React UI + Alice participant backend
Attack/                React UI + isolated attack backend modules
Bob/                   React UI + Bob participant backend
shared/backend/        FastAPI gateway and shared scientific core
*/backend/*/proxy_app.py  Local role proxies; browser credentials stay server-side
docker/                Pinned API, CUDA-Q worker, and frontend images
compose.yaml           Docker-first application topology
requirements-api.txt   Pinned API/runtime dependencies
requirements-worker.txt  SeQUeNCe and Qiskit validation dependencies
requirements.txt       Cross-platform Python dependencies
START.md                Copy-paste local startup guide
walkthrough.md          Architecture and scientific walkthrough
SECURITY_MODEL.md       Explicit adversary assumptions and claim boundaries
SCIENTIFIC_HARDENING_REPORT.md  Final evidence-backed security report
```

MySQL 9.7.2 is the application system of record and stores the persistent,
encrypted single-worker quantum job queue. Automated tests use isolated temporary
SQLite databases so tests cannot modify application data. Docker Desktop and
Docker Compose are the primary supported local runtime. Read [START.md](START.md)
to configure and start the complete stack.

## Quantum engine policy

- `cudaq`: primary research engine, isolated in the quantum-worker container. An
  explicitly enabled CPU fallback remains CUDA-Q `qpp-cpu`; it is never silent.
- `qiskit-aer`: independent circuit executor and validation backend.
- `reference`: explicit NumPy state-vector development engine.

The worker derives from the pinned NVIDIA CUDA-Q NGC image. Docker Desktop may use
WSL2 internally on Windows, but users do not manually manage a WSL Python
environment. CUDA-Q has previously been verified on this host's RTX 4050 with the
NVIDIA target; the container performs its own known-state and Bell diagnostic at
startup and records the target actually used. `scripts/verify_cudaq.py`
independently cross-checks sampled results with Qiskit Aer.

The browser applications never contain role API keys. The localhost-only frontend
container injects a different server-side key for each role and denies cross-role
routes. Use
`python scripts/create_source_archive.py` for a distributable archive; it uses an
allowlist and excludes live `.env` files, databases, builds, caches, and virtual
environments.

Final verdict: **SIH READY — WITH DOCUMENTED LIMITATIONS**. This is a genuine
discrete-qubit teleportation research simulator with empirical security experiments,
not a standardized or information-theoretically proven QDS protocol.
