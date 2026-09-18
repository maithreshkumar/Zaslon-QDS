"""
Cryptographic Hashing and QDS Workflow Schemas.
"""
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class HashCreateRequest(BaseModel):
    raw_message: str = Field(..., min_length=1, description="Original message to hash and sign")
    actor: str = Field(..., min_length=2, max_length=64, description="Signer identity")


class HashResponse(BaseModel):
    id: str
    session_id: str
    message_bytes_len: int
    sha512_digest: str
    hash_encoding_format: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
