"""
Script to validate database immutability:
Proves that historical measurement records in MySQL are strictly immutable
and are never updated, overwritten, or modified by attack mutations.
"""
import sys
import hashlib
from backend.app.db.session import SessionLocal
from backend.app.services.session_service import SessionService
from backend.app.services.hashing_service import HashingService
from backend.app.services.teleportation_service import TeleportationService
from backend.app.services.declaration_service import DeclarationService
from backend.app.services.transmission_service import TransmissionService
from backend.app.core.security import ThreatCategories
from sqlalchemy import text

def compute_measurements_fingerprint(db, quantum_run_id: str) -> str:
    """Computes a SHA-256 fingerprint over all measurement rows in order."""
    rows = db.execute(
        text("SELECT id, operation_index, prep_theta, prep_phi, expected_bit, bob_observed_bit, is_match FROM measurements WHERE quantum_run_id = :qid ORDER BY operation_index ASC"),
        {"qid": quantum_run_id}
    ).fetchall()
    
    h = hashlib.sha256()
    for row in rows:
        h.update(f"{row[0]}:{row[1]}:{row[2]}:{row[3]}:{row[4]}:{row[5]}:{row[6]}".encode())
    return h.hexdigest(), len(rows)

def main():
    print("=" * 70)
    print("ZASLON-QDS: DATABASE IMMUTABILITY VERIFICATION")
    print("=" * 70)
    
    db = SessionLocal()
    try:
        # Step 1: Create authentic session and complete quantum run
        sess = SessionService.create_session(db, session_name="Immutability-Proof-Session", created_by="Alice", verifier_id="Bob")
        hash_rec = HashingService.process_message_hash(db, sess.id, "IMMUTABLE AUDIT TEST PAYLOAD", actor="Alice")
        q_run = TeleportationService.initiate_quantum_run(db, sess.id, actor="Alice", teleportation_count=512)
        decl = DeclarationService.create_declaration(db, sess.id, signer_id="Alice")
        pkg = TransmissionService.dispatch_package(db, session_id=sess.id, sender_id="Alice", recipient_id="Bob")
        
        # Intercept and passthrough to establish initial persisted measurements
        TransmissionService.intercept_transmission(db, pkg.id, actor="Eve")
        TransmissionService.passthrough_transmission(db, pkg.id, actor="Eve")
        
        # Capture state BEFORE attack mutation
        fp_before, row_count_before = compute_measurements_fingerprint(db, q_run.id)
        print(f"\n[Measurement State BEFORE Attack Mutation]")
        print(f"  -> Target Quantum Run ID: {q_run.id}")
        print(f"  -> Persisted Row Count: {row_count_before}")
        print(f"  -> Cryptographic Rows Fingerprint: {fp_before}")
        
        # Now Eve attempts a mutation on the transmission package
        print(f"\n[Eve Action] Eve attempts mutation with ThreatCategories.FORGERY...")
        try:
            # Re-intercept package
            pkg.status = "INTERCEPTED"
            db.commit()
            TransmissionService.mutate_transmission(
                db, pkg.id,
                attack_type=ThreatCategories.FORGERY,
                mutation_params={"intensity": 0.50},
                actor="Eve"
            )
            print("  -> Eve mutation configured on transmission package.")
        except Exception as e:
            print(f"  -> Mutation attempt: {e}")
            
        # Re-capture state AFTER attack mutation
        fp_after, row_count_after = compute_measurements_fingerprint(db, q_run.id)
        print(f"\n[Measurement State AFTER Attack Mutation]")
        print(f"  -> Target Quantum Run ID: {q_run.id}")
        print(f"  -> Persisted Row Count: {row_count_after}")
        print(f"  -> Cryptographic Rows Fingerprint: {fp_after}")
        
        # Verify strict equality
        assert row_count_before == row_count_after == 512, "Row count changed!"
        assert fp_before == fp_after, "Measurement records were altered by attack mutation! Immutability violated!"
        
        print("\n[VERDICT: 100% IMMUTABLE]")
        print(f"  Fingerprint match: {fp_before == fp_after}")
        print("  Zero database rows in 'measurements' were modified or overwritten.")
        print("=" * 70)
        return True
    finally:
        db.close()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
