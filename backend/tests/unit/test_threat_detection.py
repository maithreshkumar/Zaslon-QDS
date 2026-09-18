"""
Unit and integration tests for multi-signal threat detection across all 5 threat classes:
1. Forgery (Quantum State Mismatch)
2. Impersonation (Signer Identity Spoofing)
3. Replay (Single-Use Token Reuse / Expired Freshness)
4. Unauthorized Verification (RBAC / Designated Verifier Enforcement)
5. Integrity Tampering (Message Payload Modification)
"""
import pytest
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.base import Base
from backend.app.models.session import SessionModel
from backend.app.models.hash_record import HashRecordModel
from backend.app.models.quantum_run import QuantumRunModel
from backend.app.models.measurement import MeasurementModel
from backend.app.models.declaration import PublicDeclarationModel
from backend.app.core.security import SecurityVerdicts, ThreatCategories, compute_sha512
from backend.app.services.verification_service import VerificationService
from backend.app.services.declaration_service import DeclarationService


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


def _setup_completed_session(db, session_id="test-session-001", signer="Alice", verifier="Bob", total_ops=205):
    # Create Session
    session = SessionModel(
        id=session_id,
        session_name="Threat Test Session",
        created_by=signer,
        verifier_id=verifier,
        status="DECLARATION_READY"
    )
    db.add(session)

    # Create Hash Record
    raw_msg = "Critical Financial Directive: Transfer $50,000"
    digest = compute_sha512(raw_msg.encode("utf-8"))
    hash_rec = HashRecordModel(
        id=str(uuid.uuid4()),
        session_id=session_id,
        raw_message=raw_msg,
        sha512_digest=digest,
        message_bytes_len=len(raw_msg)
    )
    db.add(hash_rec)

    # Create Completed Quantum Run
    q_run = QuantumRunModel(
        id=str(uuid.uuid4()),
        session_id=session_id,
        target_backend="default",
        teleportation_count=total_ops,
        batch_size=512,
        status="COMPLETED",
        completed_operations=total_ops
    )
    db.add(q_run)

    # Add Authentic Measurements (all matching)
    for i in range(total_ops):
        m = MeasurementModel(
            quantum_run_id=q_run.id,
            operation_index=i,
            prep_theta=0.0,
            prep_phi=0.0,
            expected_bit=0,
            alice_m0=0,
            alice_m1=0,
            bob_correction_x=0,
            bob_correction_z=0,
            bob_observed_bit=0,
            is_match=True
        )
        db.add(m)

    # Create Public Declaration
    decl = PublicDeclarationModel(
        id=str(uuid.uuid4()),
        session_id=session_id,
        signer_id=signer,
        signature_token="sig_qds_valid_token_12345",
        declaration_payload_hash="a" * 128,
        status="ACTIVE",
        is_consumed=False
    )
    db.add(decl)
    db.commit()
    return session, hash_rec, q_run, decl


def test_happy_path_verification(db_session):
    session, _, _, decl = _setup_completed_session(db_session)
    res = VerificationService.verify_session(db_session, session.id, verifier_id="Bob")

    assert res.security_decision == SecurityVerdicts.VERIFIED
    assert not res.attack_detected
    assert res.attack_category is None
    assert res.match_count > 0
    assert res.mismatch_count == 0

    # Verify declaration was consumed to prevent replay
    db_session.refresh(decl)
    assert decl.is_consumed is True
    assert decl.consumed_at is not None


def test_threat_unauthorized_verification(db_session):
    session, _, _, _ = _setup_completed_session(db_session)
    # Mallory attempts to verify instead of designated verifier Bob
    res = VerificationService.verify_session(db_session, session.id, verifier_id="Mallory_Unauthorized")

    assert res.security_decision == SecurityVerdicts.UNAUTHORIZED
    assert res.attack_detected is True
    assert res.attack_category == ThreatCategories.UNAUTHORIZED_VERIFICATION
    assert "Unauthorized verification attempt" in res.decision_reason


def test_threat_signer_impersonation(db_session):
    session, _, _, decl = _setup_completed_session(db_session)
    # Attacker Eve modifies declaration to claim she signed it
    decl.signer_id = "Eve_Impersonator"
    db_session.commit()

    res = VerificationService.verify_session(db_session, session.id, verifier_id="Bob")
    assert res.security_decision == SecurityVerdicts.REJECTED
    assert res.attack_detected is True
    assert res.attack_category == ThreatCategories.IMPERSONATION
    assert "Signer impersonation detected" in res.decision_reason


def test_threat_replay_consumed_token(db_session):
    session, _, _, decl = _setup_completed_session(db_session)
    # Mark declaration as already consumed
    decl.is_consumed = True
    decl.consumed_at = datetime.now(timezone.utc)
    decl.consumed_in_verification_id = "prior_verification_id"
    db_session.commit()

    res = VerificationService.verify_session(db_session, session.id, verifier_id="Bob")
    assert res.security_decision == SecurityVerdicts.REJECTED
    assert res.attack_detected is True
    assert res.attack_category == ThreatCategories.REPLAY
    assert "already been consumed" in res.decision_reason


def test_threat_integrity_tampering(db_session):
    session, hash_rec, _, _ = _setup_completed_session(db_session)
    # Attacker alters the raw message after digest was computed
    hash_rec.raw_message += " [UNAUTHORIZED TAMPERING: SEND TO MALLORY]"
    db_session.commit()

    res = VerificationService.verify_session(db_session, session.id, verifier_id="Bob")
    assert res.security_decision == SecurityVerdicts.INTEGRITY_FAILURE
    assert res.attack_detected is True
    assert res.attack_category == ThreatCategories.INTEGRITY_TAMPERING
    assert "tampering detected" in res.decision_reason


def test_threat_quantum_forgery_mismatch(db_session):
    session, _, q_run, _ = _setup_completed_session(db_session)
    # Alter measurement outcomes (simulating eavesdropper intercept-resend or forged state)
    meas = db_session.query(MeasurementModel).filter(MeasurementModel.quantum_run_id == q_run.id).all()
    # Flip match on 50% of measurements
    for m in meas[:len(meas)//2]:
        m.bob_observed_bit = 1 - m.expected_bit
        m.is_match = False
    db_session.commit()

    res = VerificationService.verify_session(db_session, session.id, verifier_id="Bob")
    assert res.security_decision == SecurityVerdicts.REJECTED
    assert res.attack_detected is True
    assert res.attack_category == ThreatCategories.FORGERY
    assert "High mismatch ratio" in res.decision_reason
