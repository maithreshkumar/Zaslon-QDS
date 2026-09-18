"""
Quantum Execution and Measurement Schemas.
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime


class TeleportationLaunchRequest(BaseModel):
    actor: str
    teleportation_count: Optional[int] = 4096
    batch_size: Optional[int] = 512


class QuantumRunResponse(BaseModel):
    id: str
    session_id: str
    target_backend: str
    teleportation_count: int
    batch_size: int
    completed_operations: int = 0
    failed_operations: int = 0
    current_batch: int = 0
    total_batches: int = 0
    execution_duration_ms: Optional[float] = None
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class QuantumStatusResponse(BaseModel):
    quantum_run_id: str
    session_id: str
    status: str
    teleportation_count: int
    batch_size: int
    completed_operations: int
    failed_operations: int
    current_batch: int
    total_batches: int
    progress_percentage: float
    execution_duration_ms: Optional[float] = None
    error_message: Optional[str] = None


class MeasurementResponse(BaseModel):
    id: int
    quantum_run_id: str
    operation_index: int
    prep_theta: float
    prep_phi: float
    expected_bit: int
    alice_m0: int
    alice_m1: int
    bob_correction_x: int
    bob_correction_z: int
    bob_observed_bit: int
    is_match: bool

    model_config = ConfigDict(from_attributes=True)
