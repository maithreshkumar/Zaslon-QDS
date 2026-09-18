"""
Audit Event Schemas.
"""
from pydantic import BaseModel, ConfigDict
from typing import Dict, Any, Optional
from datetime import datetime


class AuditEventResponse(BaseModel):
    id: int
    session_id: Optional[str]
    event_type: str
    actor: str
    ip_address: Optional[str]
    details: Dict[str, Any]
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
