"""
Unit tests validating all 13 Cyber & Quantum Attack Vectors in AttackSimulationService.
"""
import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.base import Base
from backend.app.models.session import SessionModel
from backend.app.models.hash_record import HashRecordModel
from backend.app.models.quantum_run import QuantumRunModel
from backend.app.models.measurement import MeasurementModel
from backend.app.models.declaration import PublicDeclarationModel
from backend.app.models.transmission import TransmissionPackageModel
from backend.app.core.security import ThreatCategories, compute_sha512
from backend.app.services.attack_simulation_service import AttackSimulationService
from backend.app.core.datetime_utils import utc_now


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def _create_test_transmission_package(db):
    session_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    decl_id = str(uuid.uuid4())
    token = f"qds_tok_{uuid.uuid4().hex}"
    msg = "SIH 26141 Classified Defense Transmission Payload"
    digest = compute_sha512(msg.encode("utf-8"))

    sess = SessionModel(
        id=session_id,
        session_name="Test Transmission Session",
        created_by="Alice",
        verifier_id="Bob",
        status="IN_TRANSIT",
        created_at=utc_now()
    )
    db.add(sess)

    h_rec = HashRecordModel(
        session_id=session_id,
        raw_message=msg,
        message_bytes_len=len(msg.encode("utf-8")),
        sha512_digest=digest,
        file_name="classified_order.pdf",
        is_binary_file=False
    )
    db.add(h_rec)

    q_run = QuantumRunModel(
        id=run_id,
        session_id=session_id,
        teleportation_count=4096,
        batch_size=512,
        status="COMPLETED",
        created_at=utc_now()
    )
    db.add(q_run)

    # Insert sample measurements
    for i in range(200):
        m = MeasurementModel(
            quantum_run_id=run_id,
            operation_index=i,
            prep_theta=1.570796,
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

    decl = PublicDeclarationModel(
        id=decl_id,
        session_id=session_id,
        signer_id="Alice",
        signature_token=token,
        declaration_payload_hash=digest,
        declared_at=utc_now(),
        is_consumed=False
    )
    db.add(decl)

    pkg = TransmissionPackageModel(
        id=str(uuid.uuid4()),
        package_tracking_no=f"PKG-{uuid.uuid4().hex[:8].upper()}",
        session_id=session_id,
        sender_id="Alice",
        recipient_id="Bob",
        status="IN_TRANSIT",
        message_payload=msg,
        committed_digest=digest,
        signature_token=token,
        quantum_run_id=run_id,
        classical_channel_status="CLEAN",
        quantum_channel_status="COHERENT",
        is_tampered=False
    )
    db.add(pkg)
    db.commit()
    return pkg


@pytest.mark.parametrize("attack_type, expected_channel, expected_status", [
    (ThreatCategories.QUANTUM_BIT_FLIP_FORGERY, "QUANTUM", "PERTURBED"),
    (ThreatCategories.QUANTUM_PHASE_FLIP_DEPOLARIZATION, "QUANTUM", "PERTURBED"),
    (ThreatCategories.QUANTUM_BASIS_ALTERATION, "QUANTUM", "PERTURBED"),
    (ThreatCategories.QUANTUM_ENTANGLEMENT_INTERCEPTION_DOS, "QUANTUM", "INTERCEPTED"),
    (ThreatCategories.ARTIFACT_METADATA_TAMPERING, "CLASSICAL", "TAMPERED"),
    (ThreatCategories.ARTIFACT_DIGEST_MISMATCH, "CLASSICAL", "TAMPERED"),
    (ThreatCategories.ARTIFACT_PAYLOAD_SUBSTITUTION, "CLASSICAL", "TAMPERED"),
    (ThreatCategories.PROTOCOL_SIGNER_IMPERSONATION, "CLASSICAL", "TAMPERED"),
    (ThreatCategories.PROTOCOL_VERIFIER_SPOOFING, "CLASSICAL", "TAMPERED"),
    (ThreatCategories.PROTOCOL_REPLAY_CONSUMED_TOKEN, "CLASSICAL", "TAMPERED"),
    (ThreatCategories.PROTOCOL_EXPIRED_WINDOW_REPLAY, "CLASSICAL", "TAMPERED"),
    (ThreatCategories.ACCESS_UNAUTHORIZED_VERIFIER_PROBE, "CLASSICAL", "INTERCEPTED"),
    (ThreatCategories.SYSTEM_CROSS_SESSION_SUBSTITUTION, "CLASSICAL", "TAMPERED"),
])
def test_all_13_attack_vectors_mutation(db_session, attack_type, expected_channel, expected_status):
    pkg = _create_test_transmission_package(db_session)
    
    result = AttackSimulationService.execute_mutation(
        db=db_session,
        transmission_id=pkg.id,
        attack_type=attack_type,
        actor="Eve_Adversary"
    )

    db_session.refresh(pkg)
    assert pkg.is_tampered is True
    assert pkg.status == "MODIFIED"
    assert pkg.active_attack_vector == attack_type
    assert pkg.tampered_channel == expected_channel
    if expected_channel == "QUANTUM":
        assert pkg.quantum_channel_status == expected_status
    else:
        assert pkg.classical_channel_status == expected_status

    assert "manipulation" in result
    assert "evidence" in result


@pytest.mark.parametrize("attack_type, expected_channel, expected_status", [
    (ThreatCategories.IMPERSONATION, "CLASSICAL", "TAMPERED"),
    (ThreatCategories.UNAUTHORIZED_VERIFICATION, "CLASSICAL", "INTERCEPTED"),
    (ThreatCategories.UNAUTHORIZED_PROBE, "CLASSICAL", "INTERCEPTED"),
    (ThreatCategories.FILE_INTEGRITY_TAMPERING, "CLASSICAL", "TAMPERED"),
    (ThreatCategories.DECLARATION_TAMPERING, "CLASSICAL", "TAMPERED"),
    (ThreatCategories.QDS_PACKAGE_TAMPERING, "CLASSICAL", "TAMPERED"),
    (ThreatCategories.FORGERY, "QUANTUM", "PERTURBED"),
    (ThreatCategories.REPLAY, "CLASSICAL", "TAMPERED"),
    (ThreatCategories.INTERCEPT_AND_RESEND, "QUANTUM", "INTERCEPTED"),
    (ThreatCategories.SESSION_SUBSTITUTION, "CLASSICAL", "TAMPERED"),
    (ThreatCategories.MEASUREMENT_MANIPULATION, "QUANTUM", "PERTURBED"),
    (ThreatCategories.BASIS_MANIPULATION, "QUANTUM", "PERTURBED"),
    (ThreatCategories.QUANTUM_STATE_REPLACEMENT, "QUANTUM", "PERTURBED"),
])
def test_canonical_13_attack_vectors_mutation(db_session, attack_type, expected_channel, expected_status):
    pkg = _create_test_transmission_package(db_session)
    
    result = AttackSimulationService.execute_mutation(
        db=db_session,
        transmission_id=pkg.id,
        attack_type=attack_type,
        actor="Eve_Adversary"
    )

    db_session.refresh(pkg)
    assert pkg.is_tampered is True
    assert pkg.status == "MODIFIED"
    assert pkg.active_attack_vector == attack_type
    assert pkg.tampered_channel == expected_channel
    if expected_channel == "QUANTUM":
        assert pkg.quantum_channel_status == expected_status
    elif expected_channel == "CLASSICAL":
        assert pkg.classical_channel_status == expected_status
    else:  # BOTH (e.g. FORGERY)
        assert pkg.classical_channel_status == "TAMPERED"

    assert "manipulation" in result
    assert "evidence" in result
