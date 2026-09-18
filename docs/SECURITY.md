# Security Architecture & Baseline — Zaslon-QDS

Defensive Security Architecture, Cryptographic Standards, and Baseline Controls for SIH 26141.

---

## 1. Security Architecture Principles

1. **Deterministic Security**: Zero black-box AI/ML models. Every authorization and threat detection check is deterministic and explainable.
2. **Defense in Depth**: Security checks are enforced at the network, API layer, domain service layer, and database constraints. Frontend restrictions are purely ergonomic.
3. **Audit Immutability**: All security-critical events (session creation, hash computation, circuit execution, declaration, verification, attacks) are logged with actors, timestamps, and metadata.
4. **Zero Credential Exposure**: Logs never contain plain passwords, secrets, private keys, or raw authentication tokens.

---

## 2. Cryptographic Standards

- **Hashing**: SHA-512 (FIPS PUB 180-4) with 512-bit output.
- **Commitments**: HMAC-SHA512 and cryptographic tokens generated using Python's `secrets` module (System CSPRNG).
- **Quantum Protocol**: 3-qubit Bell-state teleportation using standard Pauli corrections ($X, Z$).
- **Statistical Significance**: One-sided Fisher's Exact Test with significance threshold $\alpha = 0.01$.

---

## 3. Defense Against Common Vulnerabilities

| Vulnerability Vector | Defense Mechanism |
| :--- | :--- |
| **SQL Injection** | Parameterized queries enforced across all database queries via SQLAlchemy ORM. |
| **Cross-Origin Resource Sharing (CORS)** | Controlled origins and explicit headers in FastAPI CORS middleware. |
| **Insecure Direct Object References (IDOR)** | Sessions and resources identified by high-entropy UUIDv4 identifiers rather than sequential integers. |
| **Privilege Escalation** | `AuthorizationService` explicitly checks participant role membership for every sensitive mutation. |
| **Information Disclosure** | Custom domain exceptions mapped to sanitized JSON responses without exposing internal Python tracebacks. |
| **Replay Attacks** | High-entropy single-use declaration tokens and strict timestamp freshness verification. |
