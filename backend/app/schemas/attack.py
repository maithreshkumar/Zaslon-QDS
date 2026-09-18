"""
Attack Simulation and Event Schemas.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime


class AttackSimulationRequest(BaseModel):
    attack_type: str = Field(
        ...,
        pattern="^(FORGERY|IMPERSONATION|REPLAY|UNAUTHORIZED_VERIFICATION|INTEGRITY_TAMPERING)$"
    )
    tamper_payload: Optional[Dict[str, Any]] = None


class AttackEventResponse(BaseModel):
    id: str
    session_id: str
    attack_type: str
    simulated: bool
    detected: bool
    payload_manipulation: Optional[Dict[str, Any]]
    detection_evidence: Dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
