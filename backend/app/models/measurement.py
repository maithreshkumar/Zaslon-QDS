"""
Quantum Measurement Entity Model.
"""
from sqlalchemy import Column, BigInteger, String, Integer, Float, SmallInteger, Boolean, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import relationship

from ..db.base import Base


class MeasurementModel(Base):
    __tablename__ = "measurements"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    quantum_run_id = Column(String(36), ForeignKey("quantum_runs.id", ondelete="CASCADE"), nullable=False)
    operation_index = Column(Integer, nullable=False)
    prep_theta = Column(Float, nullable=False)
    prep_phi = Column(Float, nullable=False)
    expected_bit = Column(SmallInteger, nullable=False)
    alice_m0 = Column(SmallInteger, nullable=False)
    alice_m1 = Column(SmallInteger, nullable=False)
    bob_correction_x = Column(SmallInteger, nullable=False)
    bob_correction_z = Column(SmallInteger, nullable=False)
    bob_observed_bit = Column(SmallInteger, nullable=False)
    is_match = Column(Boolean, nullable=False, index=True)

    quantum_run = relationship("QuantumRunModel", back_populates="measurements")

    __table_args__ = (
        Index("idx_meas_run_op", "quantum_run_id", "operation_index"),
        UniqueConstraint("quantum_run_id", "operation_index", name="uq_run_op_idx"),
    )
