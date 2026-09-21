"""
Verification Sample and Result Entity Models.
"""
from sqlalchemy import Column, String, Integer, Float, DateTime, Enum, ForeignKey, Boolean, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from ..db.base import Base
from ..core.datetime_utils import utc_now


class VerificationSampleModel(Base):
    __tablename__ = "verification_samples"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    sample_ratio = Column(Float, default=0.05, nullable=False)
    sample_size = Column(Integer, nullable=False)
    sample_seed = Column(String(64), nullable=False)
    sampled_indices = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    session = relationship("SessionModel", back_populates="verification_samples")
    result = relationship("VerificationResultModel", back_populates="sample", uselist=False, cascade="all, delete-orphan")


class VerificationResultModel(Base):
    __tablename__ = "verification_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    transmission_id = Column(String(36), ForeignKey("transmission_packages.id", ondelete="SET NULL"), nullable=True, unique=True, index=True)
    sample_id = Column(String(36), ForeignKey("verification_samples.id", ondelete="CASCADE"), nullable=True)
    sample_size = Column(Integer, nullable=False, default=0)
    match_count = Column(Integer, nullable=False, default=0)
    mismatch_count = Column(Integer, nullable=False, default=0)
    mismatch_ratio = Column(Float, nullable=False, default=0.0)
    fisher_p_value = Column(Float, nullable=True, default=1.0)
    fisher_odds_ratio = Column(Float, nullable=True)
    contingency_table = Column(JSON, nullable=True)
    threshold_ratio = Column(Float, nullable=False, default=0.03)
    significance_alpha = Column(Float, nullable=False, default=0.01)
    baseline_error_rate = Column(Float, nullable=False, default=0.01)
    statistical_verdict = Column(
        Enum('ACCEPTABLE', 'SUSPICIOUS', 'REJECTED', name='stat_verdict_enum'),
        nullable=False
    )
    security_decision = Column(
        Enum('VERIFIED', 'REJECTED', 'UNAUTHORIZED', 'INTEGRITY_FAILURE', name='sec_decision_enum'),
        nullable=False,
        index=True
    )
    attack_detected = Column(Boolean, default=False, nullable=False)
    attack_category = Column(String(64), nullable=True)
    decision_reason = Column(Text, nullable=False)
    # File QDS and certificate receipt additions
    certificate_serial = Column(String(64), unique=True, nullable=True, index=True)
    verification_source = Column(String(32), default="IN_FLIGHT", nullable=False)  # "IN_FLIGHT" | "MANUAL_UPLOAD"
    certificate_receipt = Column(JSON, nullable=True)
    verified_at = Column(DateTime, default=utc_now, nullable=False)

    session = relationship("SessionModel", back_populates="verification_results")
    sample = relationship("VerificationSampleModel", back_populates="result")

    @property
    def odds_ratio_display(self) -> str:
        if self.fisher_odds_ratio is None:
            return "Infinity"
        return f"{self.fisher_odds_ratio:.4f}"

