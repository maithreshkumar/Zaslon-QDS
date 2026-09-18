# Architecture Specification — Zaslon-QDS

Quantum-Teleportation-Based Cyber Threat Detection for Quantum Digital Signatures (SIH 26141).

---

## 1. Architectural Foundations & Objectives

Zaslon-QDS is an engineering and research platform designed to verify quantum digital signatures and detect cyber threats against QDS infrastructure.

The platform is designed around:
* **Quantum Teleportation Foundation**: Uses a mathematically rigorous three-qubit teleportation model ($Q_0$: Message/State, $Q_1$: Alice's Bell Qubit, $Q_2$: Bob's Bell Qubit).
* **NVIDIA CUDA-Q Integration**: Real quantum circuit construction, state simulation, and measurement via CUDA-Q.
* **Deterministic Hashing**: Standard SHA-512 cryptographically bound to quantum state rotation angles.
* **Sample-based Mismatch Analysis**: 5% deterministic sampling over 4,096 teleportation operations.
* **Exact Statistical Verification**: Fisher's Exact Test against an authentic quantum channel error baseline.
* **Deterministic Cybersecurity Engine**: Role-based access control, cryptographic commitment validation, replay detection, and integrity checks.
* **Strictly No AI / ML**: Zero machine learning or heuristic black boxes; all decisions are transparent and mathematically traceable.

---

## 2. High-Level System Architecture

```text
┌────────────────────────────────────────────────────────────┐
│                       React Frontend                       │
│  - Research Dashboard       - Session Management           │
│  - QDS Pipeline Stepper     - Teleportation Circuit Viewer │
│  - Verification & Fisher UI - Threat Simulator             │
│  - Audit Trail Log                                         │
└─────────────────────────────┬──────────────────────────────┘
                              │ REST API (:8000)
┌─────────────────────────────▼──────────────────────────────┐
│                    FastAPI Backend Core                    │
│                                                            │
│  ┌────────────────────┐   ┌─────────────────────────────┐  │
│  │  Session Service   │   │     Hashing Service         │  │
│  ├────────────────────┤   ├─────────────────────────────┤  │
│  │ Teleportation Svc  │   │     Declaration Service     │  │
│  ├────────────────────┤   ├─────────────────────────────┤  │
│  │  Sampling Service  │   │     Statistics Service      │  │
│  ├────────────────────┤   ├─────────────────────────────┤  │
│  │  Verification Svc  │   │     Attack Service          │  │
│  ├────────────────────┤   ├─────────────────────────────┤  │
│  │ Authorization Svc  │   │     Audit Service           │  │
│  └────────────────────┘   └─────────────────────────────┘  │
└───────────────┬─────────────────────────────┬──────────────┘
                │                             │
                │ HTTP (:8001)                │ PyMySQL (:3306)
┌───────────────▼──────────────┐ ┌────────────▼──────────────┐
│       Quantum Engine         │ │      MySQL Database       │
│   (CUDA-Q Microservice)      │ │                           │
│  - 3-Qubit Circuit Kernel    │ │  - sessions               │
│  - State Prep (θ, φ, basis)  │ │  - participants           │
│  - Bell-Pair Generation      │ │  - hash_records           │
│  - Bell Basis Measurement    │ │  - quantum_runs           │
│  - Pauli Feed-Forward Corr   │ │  - measurements           │
│  - Target Measurement        │ │  - public_declarations    │
│  - Batch Runner              │ │  - verification_samples   │
│                              │ │  - verification_results   │
│                              │ │  - attack_events          │
│                              │ │  - audit_events           │
└──────────────────────────────┘ └───────────────────────────┘
```

---

## 3. Data Provenance and Traceability Chain

Every verification decision is completely traceable back to the raw input:

```text
Final Decision (VERIFIED / REJECTED)
   ↑
Threat Evidence & Audit Trail
   ↑
Fisher Exact Test (p-value, odds ratio)
   ↑
Contingency Table & Mismatch Ratio
   ↑
5% Deterministic Verification Sample
   ↑
4,096 Quantum Teleportation Measurements
   ↑
SHA-512 Derived State Preparation Angles
   ↑
SHA-512 512-Bit Hex Digest
   ↑
Original Plaintext Input Data
   ↑
Immutable Session UUID
```

---

## 4. Service Decoupling & Isolation

1. **Frontend**: Standalone React/TypeScript SPA served via Nginx.
2. **Backend**: Stateless FastAPI service handling orchestrations, authorization, and audit logs.
3. **Quantum Engine**: Dedicated Python microservice running in a Linux environment with `cuda-quantum` installed.
4. **Database**: MySQL 8.0 relational database with strict foreign keys and indexed query paths.
