"""
Quantum Run Entity Model.
"""
from sqlalchemy import Column, String, Integer, Float, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from ..db.base import Base
from ..core.datetime_utils import utc_now


class QuantumRunModel(Base):
    __tablename__ = "quantum_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    target_backend = Column(String(64), nullable=False, default="cudaq-default")
    teleportation_count = Column(Integer, nullable=False, default=4096)
    batch_size = Column(Integer, nullable=False, default=512)
    completed_operations = Column(Integer, nullable=False, default=0)
    failed_operations = Column(Integer, nullable=False, default=0)
    current_batch = Column(Integer, nullable=False, default=0)
    total_batches = Column(Integer, nullable=False, default=0)
    execution_duration_ms = Column(Float, nullable=True)
    status = Column(
        Enum(
            'PENDING',
            'PREPARING',
            'RUNNING',
            'PROCESSING_RESULTS',
            'COMPLETED',
            'FAILED',
            'CANCELLED',
            name='quantum_run_status_enum'
        ),
        default='PENDING',
        nullable=False
    )
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    session = relationship("SessionModel", back_populates="quantum_runs")
    measurements = relationship("MeasurementModel", back_populates="quantum_run", cascade="all, delete-orphan")

    @property
    def total_operations(self) -> int:
        return self.teleportation_count
