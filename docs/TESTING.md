# Testing & Quality Assurance Strategy — Zaslon-QDS

Verification, Testing Suites, and Validation Procedures for SIH 26141.

---

## 1. Testing Pyramid

Testing in Zaslon-QDS is structured into three tiers:

1. **Unit Testing**:
   - SHA-512 deterministic state mapping (`derive_teleportation_parameters`).
   - Contingency table calculation and Fisher Exact Test outputs.
   - Authorization role validation and token checks.
   - Replay freshness window evaluation.
2. **Integration Testing**:
   - API $\to$ Service $\to$ Database transactions.
   - Backend $\to$ Quantum Microservice HTTP contract validation.
3. **End-to-End Testing**:
   - Full workflow: Create session $\to$ SHA-512 $\to$ 4,096 Teleportations $\to$ Declaration $\to$ Verification.
   - Cyber threat detection: Forgery, Impersonation, Replay, Unauthorized Verification, Integrity Tampering.

---

## 2. Test Execution Commands

```bash
# Run backend unit tests
pytest backend/tests -v

# Verify Python syntax across all modules
python -m py_compile backend/app/main.py

# Verify TypeScript types and build
cd frontend && npx tsc --noEmit && npm run build
```
