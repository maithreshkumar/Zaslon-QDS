"""
Session and Participant Pydantic Schemas.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime


class ParticipantCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=64)
    role: str = Field(..., pattern="^(Signer|Verifier|Administrator)$")
    public_key_fingerprint: Optional[str] = None


class ParticipantResponse(BaseModel):
    id: str
    session_id: str
    name: str
    role: str
    public_key_fingerprint: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SessionCreate(BaseModel):
    session_name: str = Field(..., min_length=3, max_length=128)
    created_by: str = Field(..., min_length=2, max_length=64)
    verifier_id: str = Field(..., min_length=2, max_length=64)


class SessionResponse(BaseModel):
    id: str
    session_name: str
    status: str
    created_by: str
    verifier_id: str
    created_at: datetime
    updated_at: datetime
    participants: List[ParticipantResponse] = []

    model_config = ConfigDict(from_attributes=True)
