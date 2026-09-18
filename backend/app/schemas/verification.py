"""
Verification, Sampling, and Fisher Test Schemas.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime


class VerificationRequest(BaseModel):
    verifier_id: str = Field(..., min_length=2, max_length=64)
    sample_ratio: Optional[float] = Field(default=0.05, ge=0.01, le=1.0)


class VerificationSampleResponse(BaseModel):
    id: str
    session_id: str
    sample_ratio: float
    sample_size: int
    sample_seed: str
    sampled_indices: List[int]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VerificationResultResponse(BaseModel):
    id: str
    session_id: str
    sample_id: Optional[str] = None
    sample_size: int
    match_count: int
    mismatch_count: int
    mismatch_ratio: float
    fisher_p_value: float
    fisher_odds_ratio: Optional[float] = None
    odds_ratio_display: Optional[str] = None
    statistical_verdict: str
    security_decision: str
    attack_detected: bool
    attack_category: Optional[str]
    decision_reason: str
    verified_at: datetime
    certificate_serial: Optional[str] = None
    verification_source: Optional[str] = None
    certificate_receipt: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)
