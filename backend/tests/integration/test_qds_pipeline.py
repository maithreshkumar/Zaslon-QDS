"""
Integration tests for the complete Zaslon-QDS pipeline.
"""
import pytest
import uuid
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.base import Base
from backend.app.models.session import SessionModel
from backend.app.models.hash_record import HashRecordModel
from backend.app.models.quantum_run import QuantumRunModel
from backend.app.models.declaration import PublicDeclarationModel
from backend.app.core.security import SecurityVerdicts, ThreatCategories, compute_sha512
from backend.app.services.session_service import SessionService
from backend.app.services.hashing_service import HashingService
from backend.app.services.teleportation_service import TeleportationService
from backend.app.services.declaration_service import DeclarationService
from backend.app.services.verification_service import VerificationService
from backend.app.services.attack_service import AttackService
from quantum.service.circuits.state_prep import derive_teleportation_parameters


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()
    try:
        yield db
    finally:
        db.close()


def fake_quantum_execution(sha512_digest: str, start_index: int, batch_size: int, total_count: int = 4096):
    params = derive_teleportation_parameters(sha512_digest, total_count=total_count)
    batch = params[start_index:start_index + batch_size]
    measurements = []
    for p in batch:
        measurements.append({
            "operation_index": p["operation_index"],
            "prep_theta": p["prep_theta"],
            "prep_phi": p["prep_phi"],
            "basis": p["basis"],
            "expected_bit": p["expected_bit"],
            "alice_m0": 0,
            "alice_m1": 0,
            "bob_correction_x": 0,
            "bob_correction_z": 0,
            "bob_observed_bit": p["expected_bit"],
            "is_match": True
        })
    return {"measurements": measurements, "batch_size": len(measurements)}


def test_full_qds_pipeline_lifecycle(db_session):
    # Step 1: Initialize Session
    session = SessionService.create_session(
        db=db_session,
        session_name="QDS Pipeline Test",
        created_by="Alice_HQ",
        verifier_id="Bob_Branch"
    )
    assert session.status == "CREATED"

    # Step 2: Message Ingestion & SHA-512 Digest Computation
    raw_message = "CONFIDENTIAL: Authorize Quantum Key Distribution Handshake #26141"
    hash_rec = HashingService.process_message_hash(
        db=db_session,
        session_id=session.id,
        raw_message=raw_message,
        actor="Alice_HQ"
    )
    assert len(hash_rec.sha512_digest) == 128
    assert hash_rec.sha512_digest == compute_sha512(raw_message.encode("utf-8"))

    # Step 3: Teleportation Execution (512 operations for integration test speed)
    with patch("backend.app.services.quantum_service.QuantumService.execute_teleportation_batch", side_effect=fake_quantum_execution):
        q_run = TeleportationService.launch_teleportation(
            db=db_session,
            session_id=session.id,
            actor="Alice_HQ",
            teleportation_count=512,
            batch_size=256,
            background=False
        )
    assert q_run.status == "COMPLETED"
    assert q_run.completed_operations == 512

    # Step 4: Public Declaration by Authorized Signer
    decl = DeclarationService.create_declaration(
        db=db_session,
        session_id=session.id,
        signer_id="Alice_HQ"
    )
    assert decl.status == "ACTIVE"
    assert not decl.is_consumed

    # Step 5: Verification by Authorized Verifier Bob
    result = VerificationService.verify_session(
        db=db_session,
        session_id=session.id,
        verifier_id="Bob_Branch",
        sample_ratio=0.05
    )
    assert result.security_decision == SecurityVerdicts.VERIFIED
    assert not result.attack_detected
    assert result.sample_size == 26  # round(512 * 0.05) = 26
    assert result.mismatch_count == 0

    # Step 6: Verify Single-Use Consumption
    db_session.refresh(decl)
    assert decl.is_consumed is True
    assert decl.consumed_in_verification_id == result.id


def test_qds_pipeline_attack_and_detection(db_session):
    # Setup session through declaration
    session = SessionService.create_session(
        db=db_session,
        session_name="Attack Test Session",
        created_by="Alice_HQ",
        verifier_id="Bob_Branch"
    )
    raw_message = "Transfer $1,000,000 to Account #987654321"
    HashingService.process_message_hash(db=db_session, session_id=session.id, raw_message=raw_message, actor="Alice_HQ")
    
    with patch("backend.app.services.quantum_service.QuantumService.execute_teleportation_batch", side_effect=fake_quantum_execution):
        TeleportationService.launch_teleportation(
            db=db_session,
            session_id=session.id,
            actor="Alice_HQ",
            teleportation_count=512,
            batch_size=256,
            background=False
        )
    DeclarationService.create_declaration(db=db_session, session_id=session.id, signer_id="Alice_HQ")

    # Simulate Tampering Attack
    attack_event = AttackService.simulate_attack(
        db=db_session,
        session_id=session.id,
        attack_type=ThreatCategories.INTEGRITY_TAMPERING
    )
    assert attack_event.attack_type == ThreatCategories.INTEGRITY_TAMPERING

    # Run verification through the authentic pipeline
    result = VerificationService.verify_session(
        db=db_session,
        session_id=session.id,
        verifier_id="Bob_Branch"
    )
    assert result.security_decision == SecurityVerdicts.INTEGRITY_FAILURE
    assert result.attack_detected is True
    assert result.attack_category == ThreatCategories.INTEGRITY_TAMPERING
