"""
Transmission Package Entity Model.
Represents an in-flight QDS package transitioning from Alice -> Transmission Channel -> Eve -> Bob.
"""
from sqlalchemy import Column, String, Integer, BigInteger, DateTime, Enum, ForeignKey, Boolean, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from ..db.base import Base
from ..core.datetime_utils import utc_now


class TransmissionPackageModel(Base):
    __tablename__ = "transmission_packages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    package_tracking_no = Column(String(64), unique=True, nullable=False, index=True)
    session_id = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = Column(String(64), nullable=False, index=True)       # e.g., "Alice_Signer"
    recipient_id = Column(String(64), nullable=False, index=True)    # e.g., "Bob_Verifier"

    status = Column(
        Enum(
            'DRAFT',
            'SIGNED',
            'IN_TRANSIT',
            'INTERCEPTED',
            'PASSTHROUGH',
            'MODIFIED',
            'FORWARDED',
            'RECEIVED',
            'VERIFIED',
            'REJECTED',
            name='transmission_status_enum'
        ),
        default='DRAFT',
        nullable=False,
        index=True
    )

    # Message payload and original commitment
    message_payload = Column(Text, nullable=False)
    committed_digest = Column(String(128), nullable=False)  # Canonical SHA-512 from Alice

    # Declaration and quantum reference
    declaration_id = Column(String(36), ForeignKey("public_declarations.id", ondelete="SET NULL"), nullable=True)
    signature_token = Column(String(256), nullable=False)
    declaration_payload_hash = Column(String(128), nullable=True)
    quantum_run_id = Column(String(36), ForeignKey("quantum_runs.id", ondelete="SET NULL"), nullable=True)

    # Adversary interception & modification tracking
    intercepted_by = Column(String(64), nullable=True)  # e.g., "Eve_Attacker"
    intercepted_at = Column(DateTime, nullable=True)
    is_tampered = Column(Boolean, default=False, nullable=False)
    attack_type = Column(String(64), nullable=True)     # FORGERY, IMPERSONATION, etc.
    tamper_details = Column(JSON, nullable=True)
    forwarded_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)

    # File-based signing and dual-channel additions
    file_name = Column(String(255), nullable=True)
    file_mime_type = Column(String(128), nullable=True)
    file_size_bytes = Column(BigInteger, nullable=True)
    storage_path = Column(String(512), nullable=True)
    qds_manifest_json = Column(JSON, nullable=True)
    classical_channel_status = Column(String(64), default="NORMAL", nullable=False)
    quantum_channel_status = Column(String(64), default="COHERENT", nullable=False)
    tampered_channel = Column(String(32), nullable=True)
    active_attack_vector = Column(String(64), nullable=True)

    created_at = Column(DateTime, default=utc_now, nullable=False)

    session = relationship("SessionModel", back_populates="transmissions")
