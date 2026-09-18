"""
Verification Sampling Service.
Selects a deterministic ~5% sample of teleportation measurements for mismatch analysis.
"""
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import random
import hashlib
import uuid
import logging

from ..models.verification import VerificationSampleModel
from ..models.quantum_run import QuantumRunModel
from ..models.measurement import MeasurementModel
from ..core.config import settings
from ..core.exceptions import QuantumExecutionError
from .audit_service import AuditService

logger = logging.getLogger("zaslon.services.sampling")


class SamplingService:
    @staticmethod
    def select_sample(
        db: Session,
        session_id: str,
        sample_ratio: float = 0.05,
        seed_override: str = None
    ) -> VerificationSampleModel:
        # Retrieve latest completed quantum run
        quantum_run = db.query(QuantumRunModel).filter(
            QuantumRunModel.session_id == session_id,
            QuantumRunModel.status == "COMPLETED"
        ).order_by(QuantumRunModel.created_at.desc()).first()

        if not quantum_run:
            raise QuantumExecutionError(f"No completed quantum run found for session '{session_id}'.")

        total_ops = quantum_run.teleportation_count
        sample_size = max(1, int(round(total_ops * sample_ratio)))

        # Derive reproducible seed if not provided
        if not seed_override:
            seed_str = f"seed_{session_id}_{total_ops}_{sample_ratio}"
            seed_val = int(hashlib.sha256(seed_str.encode("utf-8")).hexdigest(), 16) % (2**32)
        else:
            seed_val = int(hashlib.sha256(seed_override.encode("utf-8")).hexdigest(), 16) % (2**32)

        rng = random.Random(seed_val)
        all_indices = list(range(total_ops))
        sampled_indices = sorted(rng.sample(all_indices, sample_size))

        sample_record = VerificationSampleModel(
            id=str(uuid.uuid4()),
            session_id=session_id,
            sample_ratio=sample_ratio,
            sample_size=sample_size,
            sample_seed=str(seed_val),
            sampled_indices=sampled_indices
        )
        db.add(sample_record)
        db.commit()
        db.refresh(sample_record)

        AuditService.log_event(
            db,
            event_type="SAMPLE_SELECTED",
            actor="system",
            session_id=session_id,
            details={
                "sample_id": sample_record.id,
                "sample_ratio": sample_ratio,
                "sample_size": sample_size,
                "sample_seed": str(seed_val)
            }
        )
        return sample_record

    @staticmethod
    def get_sampled_measurements(
        db: Session,
        sample_record: VerificationSampleModel
    ) -> List[MeasurementModel]:
        quantum_run = db.query(QuantumRunModel).filter(
            QuantumRunModel.session_id == sample_record.session_id,
            QuantumRunModel.status == "COMPLETED"
        ).order_by(QuantumRunModel.created_at.desc()).first()

        if not quantum_run:
            return []

        return db.query(MeasurementModel).filter(
            MeasurementModel.quantum_run_id == quantum_run.id,
            MeasurementModel.operation_index.in_(sample_record.sampled_indices)
        ).all()
