# Database Schema Specification — Zaslon-QDS

Relational Data Model and Persistence Architecture for SIH 26141.

---

## 1. Relational Entities Summary

The database uses **MySQL 8.0** with strict primary keys, foreign key constraints (`ON DELETE CASCADE`), indexes, and timestamping.

1. **`sessions`**: Root entity representing the lifetime of a quantum digital signature session.
2. **`participants`**: Signers, Verifiers, and Administrators assigned to a session.
3. **`hash_records`**: Plaintext message, length, and SHA-512 cryptographic digest.
4. **`quantum_runs`**: Orchestrated batch execution metadata for 4,096 teleportations.
5. **`measurements`**: Detailed record of each individual 3-qubit teleportation circuit execution.
6. **`public_declarations`**: Signer's cryptographic commitment published to the ledger.
7. **`verification_samples`**: Deterministically chosen 5% sample set with reproducible seed.
8. **`verification_results`**: Quantitative outcomes, Fisher's Exact Test $p$-value, mismatch ratio, and security decisions.
9. **`attack_events`**: Recorded simulated or live cyber threats and evidence.
10. **`audit_events`**: Tamper-evident operational audit stream.

---

## 2. Table Schemas and Indices

```sql
-- Core Foreign Key Relationships:
-- sessions(id) <--- participants(session_id)
-- sessions(id) <--- hash_records(session_id)
-- sessions(id) <--- quantum_runs(session_id)
-- quantum_runs(id) <--- measurements(quantum_run_id)
-- sessions(id) <--- public_declarations(session_id)
-- sessions(id) <--- verification_samples(session_id)
-- verification_samples(id) <--- verification_results(sample_id)
-- sessions(id) <--- attack_events(session_id)
-- sessions(id) <--- audit_events(session_id)
```

Indices are optimized for:
- Querying measurements by `(quantum_run_id, operation_index)`.
- Filtering verification results by `session_id` and `security_decision`.
- Auditing by `(session_id, event_type, timestamp)`.
