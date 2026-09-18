"""
Public Declaration Schemas.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class DeclarationCreateRequest(BaseModel):
    signer_id: str = Field(..., min_length=2, max_length=64)


class DeclarationResponse(BaseModel):
    id: str
    session_id: str
    signer_id: str
    signature_token: str
    declaration_payload_hash: str
    declared_at: datetime
    status: str
    is_consumed: bool = False
    consumed_at: Optional[datetime] = None
    consumed_in_verification_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
