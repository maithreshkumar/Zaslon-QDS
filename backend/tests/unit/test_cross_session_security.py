"""
Unit tests validating cross-session isolation and boundary controls.
"""
import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.base import Base
from backend.app.models.session import SessionModel
from backend.app.models.hash_record import HashRecordModel
from backend.app.models.quantum_run import QuantumRunModel
from backend.app.core.security import compute_sha512
from backend.app.core.exceptions import UnauthorizedError
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


def test_cross_session_signer_impersonation_blocked(db_session):
    # Session A belongs to Alice
    session_a = SessionModel(
        id="session-alpha",
        session_name="Alpha Session",
        created_by="Alice",
        verifier_id="Bob",
        status="TELEPORTED"
    )
    db_session.add(session_a)

    hash_rec = HashRecordModel(
        id=str(uuid.uuid4()),
        session_id="session-alpha",
        raw_message="Alpha message",
        sha512_digest=compute_sha512(b"Alpha message"),
        message_bytes_len=13
    )
    db_session.add(hash_rec)

    q_run = QuantumRunModel(
        id=str(uuid.uuid4()),
        session_id="session-alpha",
        target_backend="default",
        teleportation_count=512,
        batch_size=512,
        status="COMPLETED"
    )
    db_session.add(q_run)
    db_session.commit()

    # Attacker Eve attempts to issue a public declaration for Alice's session
    with pytest.raises(UnauthorizedError) as excinfo:
        DeclarationService.create_declaration(
            db=db_session,
            session_id="session-alpha",
            signer_id="Eve"
        )
    assert "not the authorized signer" in str(excinfo.value)
