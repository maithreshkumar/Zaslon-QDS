# Zaslon-QDS — 13-Step Evaluator & Demonstration Guide

## SIH 26141 — Quantum-Teleportation-Based Cyber Threat Detection for Quantum Digital Signatures

This document provides a concise, step-by-step verification and demonstration guide for judges, technical evaluators, and system operators to observe the entire Zaslon-QDS pipeline in action without mocks or simulated shortcuts.

---

### Prerequisites & Stack Status

Ensure the 4 containerized services are running:
```bash
docker compose up -d
docker compose ps
```
Expected output: 4 services (`zaslon-frontend`, `zaslon-backend`, `zaslon-quantum`, `zaslon-mysql`) in `Up` or `Up (healthy)` state.

---

### Step 1: Health & Runtime Verification

Query the central backend health endpoint:
```bash
curl http://localhost:8000/api/v1/health
```
**Expected Response**:
```json
{
  "status": "healthy",
  "database": "connected",
  "quantum_service": "connected",
  "version": "1.0.0"
}
```

---

### Step 2: Validate Real CUDA-Q Teleportation Kernel

Execute the quantum kernel unit test inside the `zaslon-quantum` microservice container to confirm real NVIDIA CUDA-Q execution:
```bash
docker exec zaslon-quantum python /app/tests/run_tests.py
```
**Expected Output**:
- Basis states $|0\rangle, |1\rangle, |+\rangle, |-\rangle$ evaluated with 100.0% fidelity.
- 128 circuits executed in ~30 ms.
- Zero mock fallbacks.

---

### Step 3: Landing Page & Protocol Architecture

Open your web browser and navigate to:
```text
http://localhost:3000
```
Verify:
- Clean, dark-mode military-grade UI showcasing the 3-actor protocol: **Alice (Signer) → Eve (Adversary) → Bob (Verifier)**.
- 1-Click Demo Access buttons for Alice, Eve, Bob, and Research/Diagnostics.
- Real-time protocol pipeline schematic with live system indicators.

---

### Step 4: Signer Operations as ALICE (`/alice`)

1. Log in or click **Launch Signer Portal** (or log in with `alice` / `zaslon2026`).
2. Compose a security directive in the directive editor.
3. Click **Create Quantum Signature (4,096 Operations)**:
   - System computes SHA-512 digest ($h = \text{SHA-512}(M)$).
   - Maps 512-bit digest deterministically to 4,096 rotation angles $(\theta_k, \phi_k)$ and bases ($Z$ or $X$).
   - Executes 4,096 3-qubit circuits on the NVIDIA CUDA-Q engine in batches of 512.
   - Seals the public declaration with commitment token (`sig_qds_...`).
4. Select designated verifier (Bob) and click **Dispatch Package to Quantum Channel**.
5. Observe status update to `IN_TRANSIT`.

---

### Step 5: Adversary Interception as EVE (`/eve`)

1. Log out or switch to Eve's portal via **Launch Adversary Lab** (or log in with `eve` / `zaslon2026`).
2. Notice the channel sniffer detects the in-flight package (`QDS-PKG-...`).
3. Click **Intercept Package** (state transitions to `INTERCEPTED`).
4. Select from the 5 attack vectors or authentic passthrough:
   - **Mode A: Zero-Tamper Passthrough**: Leave quantum states and declaration untouched.
   - **Mode B: Quantum Forgery**: Flip measurement outcome bits to distort the quantum channel.
   - **Mode C: Signer Impersonation**: Mutate the claimed signer identity to an unauthorized party.
   - **Mode D: Signature Replay**: Resubmit an expired or consumed token.
   - **Mode E: Message Tampering**: Alter plaintext after hash commitment.
   - **Mode F: Unauthorized Verification**: Attempting to invoke verification as Eve triggers an explicit RBAC barrier.
5. Click **Forward Package to Bob** (state transitions to `FORWARDED` / `RECEIVED`).

---

### Step 6: Verifier Verification as BOB (`/bob`)

1. Log out or switch to Bob's portal via **Launch Verifier Suite** (or log in with `bob` / `zaslon2026`).
2. Check Bob's secure inbox for the incoming package.
3. Click **Verify Signature using Zaslon-QDS**:
   - Executes the 11-step Zaslon-QDS verification engine.
   - Evaluates the 5-layer threat defense checklist:
     1. Signer Identity Barrier (blocks Impersonation)
     2. Verifier Authorization Barrier (blocks Unauthorized Verification)
     3. Anti-Replay Token Barrier (blocks Replay)
     4. Cryptographic Hash Barrier (blocks Message Tampering)
     5. Quantum Teleportation Channel Barrier (blocks Forgery via Fisher's Exact Test)
4. Inspect the explainable verification receipt:
   - Sample Size: 205 operations deterministically sampled (~5.0%).
   - Observed vs. Expected error contingency table ($2 \times 2$ matrix).
   - Exact hypergeometric p-value ($p \ge 0.01$ required for authentic verdict).
   - Clear verdict banner: `VERIFIED` vs `REJECTED` / `UNAUTHORIZED` / `INTEGRITY_FAILURE`.

---

### Step 7: Research Diagnostics & Real-Time Audit Trail (`/research`)

1. Log in with `admin` / `zaslon2026` or click **System Diagnostics**.
2. Inspect:
   - Live hardware status (NVIDIA CUDA-Q 0.16.0, MySQL 8.4, REST API).
   - Quantum channel parameters ($\alpha = 0.01$, threshold ratio $= 0.03$, sample ratio $= 0.05$).
   - Immutable chronologically ordered audit log containing every signing, dispatch, interception, mutation, forwarding, and verification event.

---

### Step 8: Automated Multi-Actor Workflow Script (CLI)

Execute the end-to-end multi-role test script covering authentic passthrough and all 5 attack vectors:
```bash
python scripts/e2e_role_workflow.py
```
**Expected Outcome**:
- 6/6 test scenarios pass 100%.
- Real 4,096 CUDA-Q circuits executed for each test.
- Every attack vector cleanly intercepted and categorized.

---

### Step 9: Automated Headless Chrome Browser E2E Suite

Execute the real Puppeteer browser test:
```bash
node scripts/role_browser_e2e_test.cjs
```
**Expected Outcome**:
- All 10 test stages pass.
- Role switches, JWT authentication, route guards, and UI interactions fully verified.
- **Zero console errors** (`Total Console Errors: 0`).
- **Zero page errors** (`Total Page Errors: 0`).

---

### Step 10: Backend Pytest Suite

Run the full pytest suite inside the backend container:
```bash
docker compose exec -T backend python -c "import os; os.system('PYTHONPATH=/:/backend:/quantum pytest -v')"
```
**Expected Outcome**:
- `36 passed in ~2.0s`.

---

### Step 11: System Logs & Health Inspection

Inspect container logs and system liveness:
```bash
docker compose logs --tail=50 backend
docker compose logs --tail=50 quantum-service
```
All services operate with zero unhandled exceptions, zero mock dependencies, and sub-second deterministic responses.
