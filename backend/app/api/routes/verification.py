"""
Verification and Fisher Statistical Test Routes.
"""
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from typing import List, Optional

from ...db.session import get_db
from ...services.verification_service import VerificationService
from ...models.verification import VerificationResultModel, VerificationSampleModel
from ...models.security_event import SecurityEventModel
from ...models.audit_event import AuditEventModel
from ...models.user import UserModel
from ...schemas.verification import (
    VerificationRequest,
    VerificationResultResponse,
    VerificationSampleResponse
)
from ...schemas.common import StandardResponse
from ..deps import get_current_user

router = APIRouter()


@router.post("/{session_id}/verify", response_model=StandardResponse[VerificationResultResponse], status_code=status.HTTP_200_OK)
def verify_signature(
    session_id: str,
    req: VerificationRequest,
    db: Session = Depends(get_db)
):
    result = VerificationService.verify_session(
        db=db,
        session_id=session_id,
        verifier_id=req.verifier_id,
        sample_ratio=req.sample_ratio or 0.05
    )
    return StandardResponse(data=result)


@router.get("/{session_id}/verification-results", response_model=StandardResponse[List[VerificationResultResponse]])
def get_verification_results(session_id: str, db: Session = Depends(get_db)):
    results = db.query(VerificationResultModel).filter(VerificationResultModel.session_id == session_id).all()
    return StandardResponse(data=results)


@router.get("/{session_id}/samples", response_model=StandardResponse[List[VerificationSampleResponse]])
def get_verification_samples(
    session_id: str,
    user: Optional[UserModel] = Depends(get_current_user),
    x_participant_id: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Returns private quantum verification sample indices.
    Strictly protected: Only BOB or ADMIN may inspect sample indices.
    Unauthorized probe attempts (e.g. from Eve or anonymous callers) are blocked with HTTP 403
    and recorded as UNAUTHORIZED_PROBE intrusion events.
    """
    is_authorized = False
    actor_name = "anonymous_prober"
    if user:
        actor_name = user.username
        if user.role in ["BOB", "ADMIN"]:
            is_authorized = True
    elif x_participant_id:
        actor_name = x_participant_id
        if "bob" in x_participant_id.lower() or x_participant_id.lower() == "admin":
            is_authorized = True

    if not is_authorized:
        pkg = db.query(TransmissionPackageModel).filter(TransmissionPackageModel.session_id == session_id).first()
        sec_evt = SecurityEventModel(
            session_id=session_id,
            event_type="UNAUTHORIZED_PROBE",
            severity="HIGH",
            actor=actor_name,
            resource=f"/verification/{session_id}/samples",
            details={
                "outcome": "BLOCKED",
                "http_status": 403,
                "target": "Bob-private verification resource (sample indices)",
                "actor": actor_name,
                "package_tracking_no": pkg.package_tracking_no if pkg else None,
                "message": f"Actor '{actor_name}' attempted unauthorized inspection of Bob-private sample indices."
            }
        )
        db.add(sec_evt)
        audit = AuditEventModel(
            session_id=session_id,
            actor=actor_name,
            event_type="UNAUTHORIZED_PROBE_BLOCKED",
            details={"resource": f"/verification/{session_id}/samples", "actor": actor_name}
        )
        db.add(audit)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized probe: Private quantum verification sample indices are restricted to the designated verifier."
        )

    samples = db.query(VerificationSampleModel).filter(VerificationSampleModel.session_id == session_id).all()
    return StandardResponse(data=samples)
