"""
Pydantic Schemas for Transmission Packages and Role Workflows.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime


class TransmissionPackageResponse(BaseModel):
    id: str
    package_tracking_no: str
    session_id: str
    sender_id: str
    recipient_id: str
    status: str
    message_payload: str
    committed_digest: str
    declaration_id: Optional[str] = None
    signature_token: str
    declaration_payload_hash: Optional[str] = None
    quantum_run_id: Optional[str] = None
    intercepted_by: Optional[str] = None
    intercepted_at: Optional[datetime] = None
    is_tampered: bool = False
    attack_type: Optional[str] = None
    tamper_details: Optional[Dict[str, Any]] = None
    forwarded_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    # File-based signing and dual-channel fields
    file_name: Optional[str] = None
    file_mime_type: Optional[str] = None
    file_size_bytes: Optional[int] = None
    qds_manifest_json: Optional[Dict[str, Any]] = None
    classical_channel_status: Optional[str] = "NORMAL"
    quantum_channel_status: Optional[str] = "COHERENT"
    tampered_channel: Optional[str] = None
    active_attack_vector: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BobTransmissionPackageResponse(BaseModel):
    """
    Sanitized transmission package schema delivered to Bob's verifier portal.
    Strictly omits adversary ground-truth flags (is_tampered, attack_type,
    tamper_details, tampered_channel, active_attack_vector) so that Bob evaluates
    detection solely from observable evidence.
    """
    id: str
    package_tracking_no: str
    session_id: str
    sender_id: str
    recipient_id: str
    status: str
    message_payload: str
    committed_digest: str
    declaration_id: Optional[str] = None
    signature_token: str
    declaration_payload_hash: Optional[str] = None
    quantum_run_id: Optional[str] = None
    forwarded_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    file_name: Optional[str] = None
    file_mime_type: Optional[str] = None
    file_size_bytes: Optional[int] = None
    qds_manifest_json: Optional[Dict[str, Any]] = None
    classical_channel_status: Optional[str] = "NORMAL"
    quantum_channel_status: Optional[str] = "COHERENT"
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AliceDraftRequest(BaseModel):
    document_title: str = Field(..., min_length=1, max_length=256, description="Title of signed directive")
    message_payload: str = Field(..., min_length=1, description="Message text content to sign")
    recipient_id: Optional[str] = Field("Bob_Verifier", description="Designated verifier identity")


class AliceSignResponse(BaseModel):
    session_id: str
    sha512_digest: str
    total_operations: int
    completed_operations: int
    duration_ms: float
    signature_token: str
    status: str
    file_name: Optional[str] = None
    file_size_bytes: Optional[int] = None
    qds_manifest_json: Optional[Dict[str, Any]] = None


class EveMutateRequest(BaseModel):
    attack_type: str = Field(..., description="One of the 13 supported cyber/quantum attack vectors")
    mutation_params: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Parameters for mutation")


class BobVerifyPackageRequest(BaseModel):
    sample_ratio: Optional[float] = Field(0.05, ge=0.01, le=1.0, description="Sampling ratio, default ~5%")
