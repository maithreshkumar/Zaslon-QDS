"""
Script to validate a genuine post-repair end-to-end 4,096-operation
CUDA-Q + native SeQUeNCe co-simulation workflow.
"""
import sys
import time
import hashlib
from pprint import pprint

from backend.app.db.session import SessionLocal
from backend.app.services.session_service import SessionService
from backend.app.services.hashing_service import HashingService
from backend.app.services.teleportation_service import TeleportationService
from backend.app.services.declaration_service import DeclarationService
from backend.app.services.transmission_service import TransmissionService
from backend.app.services.verification_service import VerificationService
from backend.app.models.measurement import MeasurementModel
from backend.app.core.security import SecurityVerdicts

def main():
    print("=" * 70)
    print("ZASLON-QDS: GENUINE POST-REPAIR FULL-SCALE 4,096-OPERATION VALIDATION")
    print("=" * 70)
    
    db = SessionLocal()
    try:
        t0 = time.perf_counter()
        
        # 1. Alice creates session
        print("\n[Step 1] Creating session 'FullScale-4096-Authentic-Run'...")
        sess = SessionService.create_session(db, session_name="FullScale-4096-Authentic-Run", created_by="Alice", verifier_id="Bob")
        print(f"  -> Session ID: {sess.id}")
        
        # 2. Alice hashes directive document (SHA-512)
        document_text = (
            "DEFENSE STRATEGIC DIRECTIVE 2026-QDS-ALPHA\n"
            "CO-SIMULATION PROTOCOL: 3-QUBIT TELEPORTATION (4096 OPERATIONS)\n"
            "HARDWARE BACKEND: NVIDIA CUDA-Q WITH NATIVE SEQUENCE DISCRETE-EVENT NETWORK."
        )
        print("\n[Step 2] Processing SHA-512 message hash...")
        hash_rec = HashingService.process_message_hash(db, sess.id, document_text, actor="Alice")
        print(f"  -> SHA-512 Digest: {hash_rec.sha512_digest}")
        
        # 3. Initiate Quantum Run for 4096 operations
        print("\n[Step 3] Initiating quantum run for 4,096 teleportation operations...")
        q_run = TeleportationService.initiate_quantum_run(db, sess.id, actor="Alice", teleportation_count=4096)
        print(f"  -> Quantum Run ID: {q_run.id}, Teleportation Count: {q_run.teleportation_count}")
        
        # 4. Generate Public Declaration
        print("\n[Step 4] Creating Alice's public declaration and commitment token...")
        decl = DeclarationService.create_declaration(db, sess.id, signer_id="Alice")
        print(f"  -> Signature Token: {decl.signature_token}")
        
        # 5. Dispatch Transmission Package (Alice -> In-Transit)
        print("\n[Step 5] Dispatching transmission package to Bob...")
        pkg = TransmissionService.dispatch_package(
            db,
            session_id=sess.id,
            sender_id="Alice",
            recipient_id="Bob"
        )
        print(f"  -> Tracking No: {pkg.package_tracking_no}, Status: {pkg.status}")
        
        # 6. Eve Intercepts & Passthrough
        print("\n[Step 6] Eve intercepts transmission and executes passthrough...")
        TransmissionService.intercept_transmission(db, pkg.id, actor="Eve")
        t_sim_start = time.perf_counter()
        TransmissionService.passthrough_transmission(db, pkg.id, actor="Eve")
        t_sim_end = time.perf_counter()
        print(f"  -> SeQUeNCe + CUDA-Q Co-Simulation Elapsed Time: {(t_sim_end - t_sim_start):.2f}s")
        
        # 7. Database Verification: Check persisted measurements
        print("\n[Step 7] Checking persisted measurements in database...")
        db_meas_count = db.query(MeasurementModel).filter(
            MeasurementModel.quantum_run_id == q_run.id
        ).count()
        print(f"  -> Total Measurement Records in MySQL: {db_meas_count}")
        assert db_meas_count == 4096, f"Expected 4096 measurements, got {db_meas_count}"
        
        # Check empirical match rate across all 4096
        matches = db.query(MeasurementModel).filter(
            MeasurementModel.quantum_run_id == q_run.id,
            MeasurementModel.is_match == True
        ).count()
        mismatches = db_meas_count - matches
        error_rate = mismatches / db_meas_count
        print(f"  -> Total Matches: {matches}/{db_meas_count} ({matches/db_meas_count:.2%})")
        print(f"  -> Total Mismatches: {mismatches}/{db_meas_count} (Error Rate: {error_rate:.4f})")
        
        # 8. Bob receives and verifies
        print("\n[Step 8] Bob performs 11-step verification with 5% sampling...")
        t_ver_start = time.perf_counter()
        res = VerificationService.verify_session(db, sess.id, verifier_id="Bob", transmission_id=pkg.id)
        t_ver_end = time.perf_counter()
        print(f"  -> Verification Elapsed Time: {(t_ver_end - t_ver_start)*1000:.2f}ms")
        print(f"  -> Security Decision: {res.security_decision}")
        print(f"  -> Statistical Verdict: {res.statistical_verdict}")
        print(f"  -> Sample Size: {res.sample_size} (Selected ~5% deterministically)")
        print(f"  -> Sample Matches: {res.match_count}, Mismatches: {res.mismatch_count} (Ratio: {res.mismatch_ratio:.2%})")
        print(f"  -> Fisher Exact Test p-value: {res.fisher_p_value}")
        print(f"  -> Fisher Odds Ratio: {res.fisher_odds_ratio}")
        print(f"  -> Attack Detected: {res.attack_detected}")
        print(f"  -> Decision Reason: {res.decision_reason}")
        print(f"  -> Certificate Serial: {res.certificate_serial}")
        
        assert res.security_decision == SecurityVerdicts.VERIFIED, f"Verification failed: {res.security_decision}"
        assert res.attack_detected is False
        assert res.sample_size > 200, f"Expected ~205 sample size, got {res.sample_size}"
        
        t_total = time.perf_counter() - t0
        print(f"\n[Validation Success] Complete authentic 4,096-operation run completed in {t_total:.2f}s!")
        print("=" * 70)
        return True
    finally:
        db.close()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
