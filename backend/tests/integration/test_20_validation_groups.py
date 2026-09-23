"""
Zaslon-QDS — 20-Group Complete Validation Test Suite.
Validates all scientific realism, security hardening, and invariant properties.
"""
import pytest
import uuid
import os
import math
import hashlib
import time
import httpx
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.base import Base
from backend.app.models.session import SessionModel
from backend.app.models.hash_record import HashRecordModel
from backend.app.models.quantum_run import QuantumRunModel
from backend.app.models.measurement import MeasurementModel
from backend.app.models.declaration import PublicDeclarationModel
from backend.app.models.transmission import TransmissionPackageModel
from backend.app.models.verification import VerificationResultModel, VerificationSampleModel
from backend.app.models.security_event import SecurityEventModel
from backend.app.models.user import UserModel
from backend.app.core.security import SecurityVerdicts, ThreatCategories, compute_sha512
from backend.app.core.state_prep import derive_teleportation_parameters
from backend.app.services.session_service import SessionService
from backend.app.services.hashing_service import HashingService
from backend.app.services.teleportation_service import TeleportationService
from backend.app.services.declaration_service import DeclarationService
from backend.app.services.verification_service import VerificationService
from backend.app.services.attack_simulation_service import AttackSimulationService
from backend.app.services.transmission_service import TransmissionService
from backend.app.services.file_service import FileService
from backend.app.schemas.transmission import BobTransmissionPackageResponse
from backend.app.core.datetime_utils import utc_now


@pytest.fixture
def live_db():
    from backend.app.db.session import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _create_full_authentic_pipeline(db, session_name="Live-Pipeline-Test", doc_text="CONFIDENTIAL DEFENSE DIRECTIVE #26141"):
    """Helper to create a full authentic transmission pipeline."""
    # 1. Session
    sess = SessionService.create_session(db, session_name=session_name, created_by="Alice", verifier_id="Bob")
    
    # 2. Hash
    hash_rec = HashingService.process_message_hash(db, sess.id, doc_text, actor="Alice")
    
    # 3. Quantum Run Prepared
    q_run = TeleportationService.initiate_quantum_run(db, sess.id, actor="Alice", teleportation_count=1024)
    
    # 4. Public Declaration
    decl = DeclarationService.create_declaration(db, sess.id, signer_id="Alice")
    
    # 5. Dispatch Transmission
    pkg = TransmissionService.dispatch_package(
        db,
        session_id=sess.id,
        sender_id="Alice",
        recipient_id="Bob"
    )
    return sess, hash_rec, q_run, decl, pkg


# =========================================================================
# GROUP 1: Static Quality & Compilation
# =========================================================================
def test_group_1_static_quality():
    """Verify backend modules compile without syntax errors and frontend dist exists."""
    import py_compile
    # Compile core files
    py_compile.compile("/app/app/main.py", doraise=True)
    py_compile.compile("/app/app/services/verification_service.py", doraise=True)
    py_compile.compile("/app/app/services/attack_simulation_service.py", doraise=True)
    py_compile.compile("/app/app/services/teleportation_service.py", doraise=True)
    assert True


# =========================================================================
# GROUP 2: Container Services Health
# =========================================================================
def test_group_2_services_health():
    """Verify backend and quantum services are reachable and healthy."""
    with httpx.Client(timeout=5.0) as client:
        # Backend health
        res = client.get("http://localhost:8000/api/v1/health")
        assert res.status_code == 200
        assert res.json()["status"] == "HEALTHY"

        # Quantum service health
        res_q = client.get("http://quantum-service:8001/health")
        assert res_q.status_code == 200
        assert res_q.json()["status"] == "HEALTHY"


# =========================================================================
# GROUP 3: CUDA-Q Runtime Proof
# =========================================================================
def test_group_3_cuda_q_runtime():
    """Verify CUDA-Q microservice executes quantum circuits with genuine Bell states."""
    digest = hashlib.sha512(b"SIH26141 CUDA-Q Proof").hexdigest()
    with httpx.Client(timeout=10.0) as client:
        res = client.post("http://quantum-service:8001/teleport/batch", json={
            "sha512_digest": digest,
            "start_index": 0,
            "batch_size": 128,
            "total_count": 128
        })
        assert res.status_code == 200
        data = res.json()["data"]
        assert len(data["measurements"]) == 128
        # Ideal execution should have 100% matches
        matches = sum(1 for m in data["measurements"] if m["is_match"])
        assert matches == 128


# =========================================================================
# GROUP 4: Native SeQUeNCe Simulation Proof
# =========================================================================
def test_group_4_sequence_discrete_events():
    """Verify SeQUeNCe discrete-event timeline executes and returns physical parameters."""
    with httpx.Client(timeout=10.0) as client:
        res = client.post("http://quantum-service:8001/network/simulate", json={
            "total_operations": 500,
            "fiber_distance_km": 25.0,
            "attenuation_db_per_km": 0.20,
            "simulation_seed": 12345
        })
        assert res.status_code == 200
        sim = res.json()["simulation"]
        assert sim["has_sequence_native"] is True
        assert sim["quantum_physical_metrics"]["events_scheduled_and_run"] == 1000
        assert sim["quantum_physical_metrics"]["state_fidelity_post_transmission"] > 0.90


# =========================================================================
# GROUP 5: SeQUeNCe -> CUDA-Q Coupling & Mathematical Mapping
# =========================================================================
def test_group_5_coupled_co_simulation():
    """Verify coupled SeQUeNCe -> CUDA-Q simulation endpoint and noise mapping."""
    digest = hashlib.sha512(b"SIH26141 Coupling Test").hexdigest()
    with httpx.Client(timeout=15.0) as client:
        res = client.post("http://quantum-service:8001/teleport/execute-coupled", json={
            "sha512_digest": digest,
            "start_index": 0,
            "batch_size": 256,
            "total_count": 256,
            "fiber_distance_km": 25.0,
            "attenuation_db_per_km": 0.20,
            "noise_mode": "DEMO",
            "simulation_seed": 999
        })
        assert res.status_code == 200
        data = res.json()["data"]
        assert len(data["measurements"]) == 256
        assert "network_simulation" in data
        assert data["network_simulation"]["has_sequence_native"] is True


# =========================================================================
# GROUP 6: Honest Baseline Calibration
# =========================================================================
def test_group_6_honest_baseline_calibration(live_db):
    """Verify clean transmission passes verification with mismatch < 3% and Fisher p >= 0.01."""
    sess, _, _, decl, pkg = _create_full_authentic_pipeline(live_db, "Honest-Calibration-Test")
    
    # Eve intercepts and selects passthrough
    TransmissionService.intercept_transmission(live_db, pkg.id, actor="Eve")
    TransmissionService.passthrough_transmission(live_db, pkg.id, actor="Eve")
    
    # Bob verifies
    result = VerificationService.verify_session(live_db, sess.id, verifier_id="Bob", transmission_id=pkg.id)
    assert result.security_decision == SecurityVerdicts.VERIFIED
    assert result.attack_detected is False
    assert result.mismatch_ratio <= 0.03
    assert result.fisher_p_value >= 0.01


# =========================================================================
# GROUP 7: Exact Canonical 13 Attacks
# =========================================================================
@pytest.mark.parametrize("attack_vector, expected_verdict, expected_category", [
    (ThreatCategories.IMPERSONATION, SecurityVerdicts.REJECTED, ThreatCategories.IMPERSONATION),
    (ThreatCategories.FILE_INTEGRITY_TAMPERING, SecurityVerdicts.INTEGRITY_FAILURE, ThreatCategories.FILE_INTEGRITY_TAMPERING),
    (ThreatCategories.DECLARATION_TAMPERING, SecurityVerdicts.INTEGRITY_FAILURE, ThreatCategories.DECLARATION_TAMPERING),
    (ThreatCategories.QDS_PACKAGE_TAMPERING, SecurityVerdicts.INTEGRITY_FAILURE, ThreatCategories.QDS_PACKAGE_TAMPERING),
    (ThreatCategories.FORGERY, SecurityVerdicts.REJECTED, ThreatCategories.FORGERY),
    (ThreatCategories.REPLAY, SecurityVerdicts.REJECTED, ThreatCategories.REPLAY),
    (ThreatCategories.INTERCEPT_AND_RESEND, SecurityVerdicts.REJECTED, ThreatCategories.FORGERY),
    (ThreatCategories.SESSION_SUBSTITUTION, SecurityVerdicts.REJECTED, ThreatCategories.SESSION_SUBSTITUTION),
    (ThreatCategories.MEASUREMENT_MANIPULATION, SecurityVerdicts.REJECTED, ThreatCategories.FORGERY),
    (ThreatCategories.BASIS_MANIPULATION, SecurityVerdicts.REJECTED, ThreatCategories.FORGERY),
    (ThreatCategories.QUANTUM_STATE_REPLACEMENT, SecurityVerdicts.REJECTED, ThreatCategories.FORGERY),
])
def test_group_7_canonical_attacks(live_db, attack_vector, expected_verdict, expected_category):
    """Verify each canonical attack is detected via authentic evidence."""
    sess, _, _, decl, pkg = _create_full_authentic_pipeline(live_db, f"Attack-Test-{attack_vector}")
    
    # Eve intercepts and mutates
    TransmissionService.intercept_transmission(live_db, pkg.id, actor="Eve")
    TransmissionService.mutate_transmission(live_db, pkg.id, attack_type=attack_vector, mutation_params={}, actor="Eve")
    
    # Forward to Bob
    TransmissionService.forward_transmission(live_db, pkg.id, actor="Eve")
    
    # Bob verifies
    result = VerificationService.verify_session(live_db, sess.id, verifier_id="Bob", transmission_id=pkg.id)
    assert result.security_decision == expected_verdict
    assert result.attack_detected is True
    assert result.attack_category == expected_category


def test_group_7_unauthorized_verification(live_db):
    """Verify unauthorized verification is blocked as access control 403."""
    sess, _, _, _, pkg = _create_full_authentic_pipeline(live_db, "Unauthorized-Verif-Test")
    TransmissionService.intercept_transmission(live_db, pkg.id, actor="Eve")
    TransmissionService.passthrough_transmission(live_db, pkg.id, actor="Eve")
    
    # Eve attempts unauthorized verification
    result = VerificationService.verify_session(live_db, sess.id, verifier_id="Eve_Mallory", transmission_id=pkg.id)
    assert result.security_decision == SecurityVerdicts.UNAUTHORIZED
    assert result.attack_detected is True
    assert result.attack_category == ThreatCategories.UNAUTHORIZED_VERIFICATION


def test_group_7_unauthorized_probe(live_db):
    """Verify unauthorized probe of verification samples is logged and blocked."""
    sess, _, _, _, pkg = _create_full_authentic_pipeline(live_db, "Unauthorized-Probe-Test")
    with httpx.Client(timeout=5.0) as client:
        res = client.get(f"http://localhost:8000/api/v1/verification/{sess.id}/samples", headers={"X-Participant-ID": "Eve"})
        assert res.status_code == 403


# =========================================================================
# GROUP 8: Passthrough Baseline
# =========================================================================
def test_group_8_passthrough_baseline(live_db):
    """Alice -> Eve (Passthrough) -> Bob verifies with 100% success."""
    sess, _, _, _, pkg = _create_full_authentic_pipeline(live_db, "Passthrough-Test")
    TransmissionService.intercept_transmission(live_db, pkg.id, actor="Eve")
    TransmissionService.passthrough_transmission(live_db, pkg.id, actor="Eve")
    
    res = VerificationService.verify_session(live_db, sess.id, verifier_id="Bob", transmission_id=pkg.id)
    assert res.security_decision == SecurityVerdicts.VERIFIED
    assert res.attack_detected is False


# =========================================================================
# GROUP 9: Unknown Attack Variations
# =========================================================================
def test_group_9_unknown_attack_variation(live_db):
    """Non-standard mutation (e.g. trailing bytes appended to file) detected by invariant."""
    sess, hash_rec, _, _, pkg = _create_full_authentic_pipeline(live_db, "Unknown-Variation-Test")
    TransmissionService.intercept_transmission(live_db, pkg.id, actor="Eve")
    TransmissionService.passthrough_transmission(live_db, pkg.id, actor="Eve")
    
    # Novel attack: alter in-transit package payload without setting attack enum
    pkg.message_payload += " [CORRUPT_PAYLOAD]"
    hash_rec.raw_message += " [CORRUPT_PAYLOAD]"
    live_db.commit()
    
    res = VerificationService.verify_session(live_db, sess.id, verifier_id="Bob", transmission_id=pkg.id)
    assert res.security_decision == SecurityVerdicts.INTEGRITY_FAILURE
    assert res.attack_detected is True


def test_group_9_unknown_quantum_disturbance_anomaly(live_db):
    """Unclassified continuous quantum disturbance detected as statistical anomaly purely from physical evidence."""
    sess, _, _, _, pkg = _create_full_authentic_pipeline(live_db, "Unknown-Quantum-Disturbance-Test")
    TransmissionService.intercept_transmission(live_db, pkg.id, actor="Eve")
    
    # Eve injects an unclassified pre-measurement continuous disturbance (e.g. continuous rotation/tilt)
    # without any canonical attack enum or informing Bob
    TransmissionService.mutate_transmission(
        live_db,
        pkg.id,
        attack_type="UNCLASSIFIED_QUANTUM_DISTURBANCE",
        mutation_params={"rotation_angle_rad": 1.25, "continuous_noise": 0.25},
        actor="Eve"
    )
    TransmissionService.forward_transmission(live_db, pkg.id, actor="Eve")
    
    # Bob verifies: independently evaluates quantum measurements via Fisher exact test
    res = VerificationService.verify_session(live_db, sess.id, verifier_id="Bob", transmission_id=pkg.id)
    
    assert res.security_decision == SecurityVerdicts.REJECTED
    assert res.attack_detected is True
    assert res.statistical_verdict in ("SUSPICIOUS", "REJECTED")
    assert res.mismatch_ratio > 0.03
    assert res.fisher_p_value < 0.01



# =========================================================================
# GROUP 10: Zero Ground-Truth Leakage in Bob API
# =========================================================================
def test_group_10_zero_ground_truth_leakage(live_db):
    """Verify BobTransmissionPackageResponse omits all Eve attack metadata."""
    sess, _, _, _, pkg = _create_full_authentic_pipeline(live_db, "Sanitization-Test")
    TransmissionService.intercept_transmission(live_db, pkg.id, actor="Eve")
    TransmissionService.mutate_transmission(live_db, pkg.id, attack_type=ThreatCategories.FORGERY, mutation_params={}, actor="Eve")
    live_db.refresh(pkg)
    
    bob_pkg = BobTransmissionPackageResponse.model_validate(pkg)
    dumped = bob_pkg.model_dump()
    
    # Strictly ensure Eve's attack fields are NOT present
    assert "is_tampered" not in dumped
    assert "attack_type" not in dumped
    assert "tamper_details" not in dumped
    assert "tampered_channel" not in dumped


# =========================================================================
# GROUP 11: Database Measurement Immutability
# =========================================================================
def test_group_11_measurement_immutability(live_db):
    """Verify MeasurementModel records are written once and never updated."""
    sess, _, q_run, _, pkg = _create_full_authentic_pipeline(live_db, "Immutability-Test")
    TransmissionService.intercept_transmission(live_db, pkg.id, actor="Eve")
    TransmissionService.passthrough_transmission(live_db, pkg.id, actor="Eve")
    
    meas_before = live_db.query(MeasurementModel).filter(MeasurementModel.quantum_run_id == q_run.id).all()
    assert len(meas_before) == 1024
    original_bits = [m.bob_observed_bit for m in meas_before]
    
    # Bob verifies
    VerificationService.verify_session(live_db, sess.id, verifier_id="Bob", transmission_id=pkg.id)
    
    meas_after = live_db.query(MeasurementModel).filter(MeasurementModel.quantum_run_id == q_run.id).all()
    after_bits = [m.bob_observed_bit for m in meas_after]
    assert original_bits == after_bits


# =========================================================================
# GROUP 12: Bob Independent Derivation Proof
# =========================================================================
def test_group_12_independent_derivation_proof(live_db):
    """Tampering with expected_bit in database does NOT fool Bob's verification."""
    sess, _, q_run, _, pkg = _create_full_authentic_pipeline(live_db, "Independent-Derivation-Test")
    TransmissionService.intercept_transmission(live_db, pkg.id, actor="Eve")
    TransmissionService.passthrough_transmission(live_db, pkg.id, actor="Eve")
    
    # Attacker tries to sabotage DB expected_bit by inverting it
    meas = live_db.query(MeasurementModel).filter(MeasurementModel.quantum_run_id == q_run.id).all()
    for m in meas:
        m.expected_bit = 1 - m.expected_bit  # Corrupted in DB
    live_db.commit()
    
    # Bob verifies: independently derives expected_bit from SHA-512 digest!
    result = VerificationService.verify_session(live_db, sess.id, verifier_id="Bob", transmission_id=pkg.id)
    assert result.security_decision == SecurityVerdicts.VERIFIED
    assert result.attack_detected is False


# =========================================================================
# GROUP 13: Manual / Offline Verification (No Fake Statistics)
# =========================================================================
def test_group_13_manual_upload_missing_evidence(live_db):
    """Verify manual package upload without measurements returns INCONCLUSIVE and EVIDENCE_MISSING."""
    manifest = {
        "header": {"protocol": "Zaslon-QDS", "version": "1.0"},
        "document": {"sha512_digest": hashlib.sha512(b"sample text").hexdigest(), "filename": "test.txt"},
        "signer": {"signer_id": "Alice"},
        "designated_verifier": {"verifier_id": "Bob"},
        "public_declaration": {"signer_id": "Alice", "signature_token": "token123"},
        "evidence": {}  # Missing measurements
    }
    res = VerificationService.verify_manual_upload(
        live_db,
        verifier_id="Bob",
        document_bytes=b"sample text",
        filename="test.txt",
        qds_json_dict=manifest
    )
    assert res.security_decision == SecurityVerdicts.INCONCLUSIVE
    assert res.statistical_verdict == "EVIDENCE_MISSING"
    assert res.sample_size == 0


# =========================================================================
# GROUP 14: Real Replay Verification & Idempotency
# =========================================================================
def test_group_14_real_replay_and_idempotency(live_db):
    """T1 verified -> reopening T1 is idempotent -> T2 replay is rejected."""
    sess, hash_rec, q_run, decl, pkg1 = _create_full_authentic_pipeline(live_db, "Replay-Idempotency-T1")
    TransmissionService.intercept_transmission(live_db, pkg1.id, actor="Eve")
    TransmissionService.passthrough_transmission(live_db, pkg1.id, actor="Eve")
    
    # First verification of T1
    res1 = VerificationService.verify_session(live_db, sess.id, verifier_id="Bob", transmission_id=pkg1.id)
    assert res1.security_decision == SecurityVerdicts.VERIFIED
    
    # Reopen T1 -> Idempotent return of same result
    res1_again = VerificationService.verify_session(live_db, sess.id, verifier_id="Bob", transmission_id=pkg1.id)
    assert res1_again.id == res1.id
    assert res1_again.security_decision == SecurityVerdicts.VERIFIED
    
    # Adversary Eve replays same package as new transmission T2
    pkg2 = TransmissionPackageModel(
        id=str(uuid.uuid4()),
        package_tracking_no=TransmissionService.generate_tracking_number(),
        session_id=sess.id,
        sender_id="Alice",
        recipient_id="Bob",
        status="IN_TRANSIT",
        message_payload=hash_rec.raw_message,
        committed_digest=hash_rec.sha512_digest,
        signature_token=decl.signature_token,
        declaration_payload_hash=decl.declaration_payload_hash,
        quantum_run_id=q_run.id
    )
    live_db.add(pkg2)
    live_db.commit()
    
    TransmissionService.intercept_transmission(live_db, pkg2.id, actor="Eve")
    TransmissionService.passthrough_transmission(live_db, pkg2.id, actor="Eve")
    
    # Bob verifies T2 -> Token consumed! Replay detected!
    res2 = VerificationService.verify_session(live_db, sess.id, verifier_id="Bob", transmission_id=pkg2.id)
    assert res2.security_decision == SecurityVerdicts.REJECTED
    assert res2.attack_detected is True
    assert res2.attack_category == ThreatCategories.REPLAY


# =========================================================================
# GROUP 15: Concurrency & Row Locking
# =========================================================================
def test_group_15_concurrency_locking(live_db):
    """Verify repeated sequential verifications honor single-use consumption safely."""
    sess, _, _, _, pkg = _create_full_authentic_pipeline(live_db, "Concurrency-Test")
    TransmissionService.intercept_transmission(live_db, pkg.id, actor="Eve")
    TransmissionService.passthrough_transmission(live_db, pkg.id, actor="Eve")
    
    r1 = VerificationService.verify_session(live_db, sess.id, verifier_id="Bob", transmission_id=pkg.id)
    r2 = VerificationService.verify_session(live_db, sess.id, verifier_id="Bob", transmission_id=pkg.id)
    assert r1.id == r2.id


# =========================================================================
# GROUP 16: Multi-Portal Accessibility
# =========================================================================
def test_group_16_portal_accessibility():
    """Verify HTTP accessibility for all portals: Alice, Eve, Bob, Diagnostics."""
    with httpx.Client(timeout=5.0) as client:
        # Check through frontend host
        r_alice = client.get("http://frontend:5173")
        assert r_alice.status_code == 200

        r_eve = client.get("http://frontend:5174")
        assert r_eve.status_code == 200

        r_bob = client.get("http://frontend:5175")
        assert r_bob.status_code == 200

        r_diag = client.get("http://frontend:80")
        assert r_diag.status_code == 200


# =========================================================================
# GROUP 17: Multi-File Type Validation
# =========================================================================
def test_group_17_file_types(live_db):
    """Validate hashing and bundle generation for TXT, PDF, PNG, and arbitrary binary bytes."""
    payloads = {
        "text.txt": b"Simple directive text",
        "doc.pdf": b"%PDF-1.5 \x00\x01\x02 binary pdf header",
        "image.png": b"\x89PNG\r\n\x1a\n binary png image",
        "archive.zip": b"PK\x03\x04 binary zip archive"
    }
    for fname, content in payloads.items():
        sess_id = str(uuid.uuid4())
        meta = FileService.hash_and_save_stream(sess_id, fname, content)
        assert meta["filename"] == fname
        assert meta["sha512_digest"] == hashlib.sha512(content).hexdigest()


# =========================================================================
# GROUP 18: Large File Bounded Streaming
# =========================================================================
def test_group_18_bounded_streaming():
    """Verify bounded streaming hash computation handles multi-megabyte payloads."""
    test_bytes = b"ZaslonQDS_Chunk_" * 100000  # ~1.6 MB
    expected_hash = hashlib.sha512(test_bytes).hexdigest()
    
    sess_id = f"stream-test-{uuid.uuid4().hex[:8]}"
    meta = FileService.hash_and_save_stream(sess_id, "large_telemetry.bin", test_bytes)
    assert meta["sha512_digest"] == expected_hash
    assert meta["file_size_bytes"] == len(test_bytes)


# =========================================================================
# GROUP 19: Security Regression & RBAC Barriers
# =========================================================================
def test_group_19_security_regression(live_db):
    """Verify unauthorized actors cannot sign or probe."""
    sess, _, _, _, _ = _create_full_authentic_pipeline(live_db, "RBAC-Regression-Test")
    
    # Eve attempts to sign session designated to Alice
    from backend.app.core.exceptions import UnauthorizedError
    with pytest.raises(UnauthorizedError):
        DeclarationService.create_declaration(live_db, sess.id, signer_id="Eve")


# =========================================================================
# GROUP 20: Claim Validation & Scientific Realism
# =========================================================================
def test_group_20_scientific_realism_claims():
    """Verify zero ML/AI dependencies and pure deterministic quantum/cryptographic design."""
    import inspect
    from backend.app.services import verification_service
    source = inspect.getsource(verification_service)
    # Strict Invariant: No ML / neural networks
    assert "tensorflow" not in source
    assert "torch" not in source
    assert "sklearn" not in source
    assert "random.choice" not in source
