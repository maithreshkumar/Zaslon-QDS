# Zaslon-QDS

> **Quantum-Teleportation-Based Cyber Threat Detection for Quantum Digital Signatures**  
> Problem Statement: **SIH 26141**

---

## 1. Overview

**Zaslon-QDS** is a production-grade cybersecurity research platform that harnesses **3-qubit quantum teleportation**, **NVIDIA CUDA-Q**, **SHA-512 cryptographic hashing**, **sample-based mismatch analysis**, **Fisher's Exact Test**, and **deterministic cybersecurity rules** to protect and verify Quantum Digital Signatures (QDS).

The system is strictly deterministic and free of machine learning or artificial intelligence. Every verification decision is explainable and mathematically rooted in quantum mechanics, cryptographic hashing, and hypergeometric statistical hypothesis testing.

---

## 2. Key Capabilities

* **3-Qubit Quantum Teleportation Model**: Authentic implementation using Message ($Q_0$), Alice Bell ($Q_1$), and Bob Bell ($Q_2$) qubits with classical feed-forward Pauli corrections ($X^{m_1} Z^{m_0}$).
* **NVIDIA CUDA-Q Engine**: Real quantum circuit construction, simulation, and execution via a dedicated containerized quantum microservice.
* **4,096 Teleportation Workload**: Configurable high-assurance signature workload with batched execution and real-time progress reporting.
* **Deterministic SHA-512 State Mapping**: Cryptographic digest expansion into exact single-qubit rotation angles ($\theta_k, \phi_k$) and bases ($Z$ or $X$).
* **5% Verification Sampling**: Pseudo-random sampling seeded deterministically for reproducibility.
* **Fisher's Exact Test**: Exact hypergeometric contingency evaluation against a 1% quantum channel error baseline.
* **Cyber Threat Detection**: Intercepts 5 major threat classes:
  1. *Forgery* (state manipulation)
  2. *Impersonation* (unauthorized participant identity)
  3. *Replay Attacks* (reused declaration tokens)
  4. *Unauthorized Verification* (access control violations)
  5. *Integrity Tampering* (payload tampering after hashing)
* **Full Data Provenance**: Every verdict traces back from final decision $\to$ Fisher test $\to$ mismatch ratio $\to$ 5% sample $\to$ 4,096 teleportations $\to$ SHA-512 $\to$ input message $\to$ session UUID.

---

## 3. Technology Stack

| Layer | Technology | Responsibility |
| :--- | :--- | :--- |
| **Frontend** | React 18, Vite, TypeScript, Tailwind CSS, Lucide-React, Recharts | Interactive research dashboard, circuit visualizer, threat simulator |
| **Backend API** | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0 | Modular REST API, authorization, audit logging, pipeline orchestration |
| **Quantum Engine** | NVIDIA CUDA-Q (`cuda-quantum`), Python 3.12 | 3-qubit teleportation kernel execution and measurement |
| **Database** | MySQL 8.0 / MariaDB | Relational persistence for 10 domain entities |
| **Cryptography** | Standard `hashlib` (SHA-512), `hmac`, `secrets` | Digest computation, commitment tokens, integrity verification |
| **Statistics** | `scipy.stats.fisher_exact`, `numpy` | Fisher's Exact Test, odds ratio, contingency table evaluation |
| **Deployment** | Docker, Docker Compose | Multi-service containerization (`frontend`, `backend`, `quantum-service`, `mysql-db`) |


---

## 4. Role-Based Multi-Actor Architecture (Alice → Eve → Bob)

Instead of a generic centralized dashboard, Zaslon-QDS is organized around three distinct actor experiences representing the authentic protocol lifecycle:

```text
┌────────────────────────────────┐
│       ALICE (Signer Portal)    │
│  - Compose Plaintext Directive │
│  - Compute SHA-512 Digest      │
│  - 4,096 CUDA-Q Circuits       │
│  - Seal Public Declaration     │
│  - Dispatch to Quantum Channel │
└───────────────┬────────────────┘
                │
                ▼ (In Transit: QDS-PKG-...)
┌────────────────────────────────┐
│        EVE (Adversary Lab)     │
│  - Real-Time Channel Sniffer   │
│  - Intercept In-Flight Package │
│  - 5 Threat Injection Modes    │
│    • State/Bit Forgery         │
│    • Signer Impersonation      │
│    • Token Replay              │
│    • Unauthorized Verification │
│    • Message Tampering         │
│  - Zero-Tamper Passthrough     │
│  - Forward to Verifier         │
└───────────────┬────────────────┘
                │
                ▼ (Forwarded Package)
┌────────────────────────────────┐
│      BOB (Verifier Suite)      │
│  - Secure Received Inbox       │
│  - Manifest & Commitment Check │
│  - 11-Step Zaslon-QDS Pipeline │
│  - 5-Layer Defense Barriers    │
│  - Deterministic 5% Sampling   │
│  - Fisher's Exact Test Receipt │
│  - Immutable Audit Ledger      │
└────────────────────────────────┘
```

---

## 5. Getting Started

### Prerequisites
* **Docker** (v24.0+) & **Docker Compose** (v2.20+)
* Optional for bare-metal host scripts: Python 3.12+, Node.js 20+

### Step 1: Environment Setup
Clone the repository and copy the environment configuration template:
```bash
cp .env.example .env
```

### Step 2: Build and Launch
Launch all 4 containerized services with Docker Compose:
```bash
docker compose up --build -d
```

### Step 3: Verify Service Health
Check that all components are healthy:
```bash
curl http://localhost:8000/api/v1/health
```

### Step 4: Access User Interface
Open your browser and navigate to:
```text
http://localhost:3000
```

### Pre-Seeded Demo Credentials
| Role | Portal Route | Username | Password | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **Alice** | `/alice` | `alice` | `zaslon2026` | Sign messages, run 4,096 CUDA-Q circuits, dispatch packages |
| **Eve** | `/eve` | `eve` | `zaslon2026` | Intercept channel packages, inject 5 attack vectors, forward |
| **Bob** | `/bob` | `bob` | `zaslon2026` | Inspect inbox, verify QDS, check Fisher test & defense barriers |
| **Admin** | `/research` | `admin` | `zaslon2026` | Hardware telemetry, CUDA-Q runtime diagnostics, audit stream |

---

## 6. End-to-End Signature Workflow

1. **Alice Signs & Dispatches**:
   - Alice logs in at `/alice`, types a security directive, and clicks **Create Quantum Signature (4,096 Operations)**.
   - SHA-512 hashes the directive into rotation angles ($\theta_k, \phi_k$) and bases ($Z$ or $X$).
   - 4,096 3-qubit circuits execute on NVIDIA CUDA-Q; public declaration and commitment token are generated.
   - Alice clicks **Dispatch Package to Quantum Channel**.
2. **Eve Intercepts in Transit**:
   - Eve logs in at `/eve`, views the channel sniffer, and clicks **Intercept Package**.
   - Eve chooses either **Passthrough (Zero Tampering)** or injects one of the 5 attack vectors (e.g. Forgery, Impersonation, Tampering).
   - Eve clicks **Forward Package to Bob**.
3. **Bob Verifies & Audits**:
   - Bob logs in at `/bob`, sees the incoming package in his secure inbox, and clicks **Verify Signature using Zaslon-QDS**.
   - The 11-step verification engine evaluates signer identity, authorizations, anti-replay, message integrity, and deterministic 5% quantum sample mismatch against Fisher's Exact Test ($p \ge 0.01$).
   - Bob reviews the explainable receipt, contingency matrix, and 5-layer defense status (`VERIFIED` or `REJECTED`).

---

## 7. Real Validation Commands

Execute the real verification suites against the live Docker stack:

```bash
# 1. Real CUDA-Q Basis States Test (inside container)
docker exec zaslon-quantum python /app/tests/run_tests.py

# 2. Complete Multi-Role End-to-End Workflow & Attack Scenarios (6/6 Pass)
python scripts/e2e_role_workflow.py

# 3. Chrome Headless Browser E2E UI Validation (Alice -> Eve -> Bob, 0 Console Errors)
node scripts/role_browser_e2e_test.cjs

# 4. Backend Pytest Unit & Integration Tests (36 passed, 100%)
docker compose exec -T backend python -c "import os; os.system('PYTHONPATH=/:/backend:/quantum pytest -v')"

# 5. Legacy 4,096-Operation Teleportation Benchmark & Attack Validation
python scripts/e2e_4096_benchmark.py
python scripts/e2e_attack_validation.py
```

---

## 8. Project Documentation

* [Evaluator Demo Guide (13 Steps)](docs/DEMO_GUIDE.md)
* [Scientific & Engineering Limitations](docs/LIMITATIONS.md)
* [Architecture Specification](docs/ARCHITECTURE.md)
* [QDS Workflow Details](docs/QDS_WORKFLOW.md)
* [Quantum Teleportation Theory & CUDA-Q](docs/QUANTUM_TELEPORTATION.md)
* [Cyber Threat Detection & Simulation](docs/ATTACK_DETECTION.md)
* [Security Baseline](docs/SECURITY.md)
* [API Reference](docs/API.md)
* [Database Schema](docs/DATABASE.md)
* [Docker Topology](docs/DOCKER.md)
* [Testing & QA](docs/TESTING.md)

---

## 9. SIH 26141 Compliance & Completion Status

Zaslon-QDS has completed all implementation and role-restructuring phases. The platform provides a production-grade, end-to-end operational research system with real quantum circuit execution on NVIDIA CUDA-Q, bulk MySQL persistence, statistical hypothesis verification via Fisher's Exact Test, defense against 5 threat vectors, role-isolated actor portals (Alice $\to$ Eve $\to$ Bob), and zero browser console errors.

