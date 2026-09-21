"""
Eve (Attacker / Adversary) API Router.
Dedicated to Eve's interception, cyber attack experimentation, passthrough, and forwarding workflows.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List

from ...db.session import get_db
from ...models.user import UserModel
from ...models.transmission import TransmissionPackageModel
from ...models.session import SessionModel
from ...models.attack_event import AttackEventModel
from ...models.audit_event import AuditEventModel
from ...models.security_event import SecurityEventModel
from ...services.transmission_service import TransmissionService
from ...schemas.transmission import (
    TransmissionPackageResponse,
    EveMutateRequest
)
from ..deps import require_role

router = APIRouter(tags=["Eve — Adversary Lab"])


@router.get("/interceptable", response_model=List[TransmissionPackageResponse])
def list_interceptable_transmissions(
    user: UserModel = Depends(require_role(["EVE", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """Eve sniffs the communication channel and lists available in-flight packages."""
    return TransmissionService.get_interceptable_transmissions(db)


@router.get("/channel-telemetry/{transmission_id}")
def get_channel_telemetry(
    transmission_id: str,
    user: UserModel = Depends(require_role(["EVE", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """Provides Eve's sniffer with detailed split-screen Classical and Quantum channel telemetry."""
    try:
        return TransmissionService.get_channel_telemetry(db, transmission_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


def _handle_transmission_error(e: ValueError):
    msg = str(e)
    if "not found" in msg.lower():
        raise HTTPException(status_code=404, detail=msg)
    raise HTTPException(status_code=409, detail=msg)


@router.post("/intercept/{transmission_id}", response_model=TransmissionPackageResponse)
def intercept_transmission(
    transmission_id: str,
    user: UserModel = Depends(require_role(["EVE", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """Eve intercepts a transmission package from the channel (pauses transit to Bob)."""
    try:
        return TransmissionService.intercept_transmission(db, transmission_id, actor=user.username)
    except ValueError as e:
        _handle_transmission_error(e)


@router.post("/mutate/{transmission_id}", response_model=TransmissionPackageResponse)
def mutate_transmission(
    transmission_id: str,
    request: EveMutateRequest,
    user: UserModel = Depends(require_role(["EVE", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """
    Eve injects a controlled cyber threat into the intercepted package:
    - FORGERY: Inverts measurement bits to disrupt quantum teleportation evidence.
    - IMPERSONATION: Modifies declaration signer to claim Alice's identity.
    - REPLAY: Replaces signature token with already-consumed credentials.
    - INTEGRITY_TAMPERING: Mutates plaintext message payload after hash was committed.
    Note: Eve does NOT know the final verification verdict; Bob evaluates it upon receipt.
    """
    try:
        return TransmissionService.mutate_transmission(
            db,
            transmission_id=transmission_id,
            attack_type=request.attack_type,
            mutation_params=request.mutation_params or {},
            actor=user.username
        )
    except ValueError as e:
        _handle_transmission_error(e)


@router.post("/passthrough/{transmission_id}", response_model=TransmissionPackageResponse)
def passthrough_transmission(
    transmission_id: str,
    user: UserModel = Depends(require_role(["EVE", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """Eve elects not to tamper with the transmission, leaving all quantum & classical material authentic."""
    try:
        return TransmissionService.passthrough_transmission(db, transmission_id, actor=user.username)
    except ValueError as e:
        _handle_transmission_error(e)


@router.post("/forward/{transmission_id}", response_model=TransmissionPackageResponse)
def forward_transmission(
    transmission_id: str,
    user: UserModel = Depends(require_role(["EVE", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """Eve dispatches the package onwards to Bob's inbox (state transitions to RECEIVED)."""
    try:
        return TransmissionService.forward_transmission(db, transmission_id, actor=user.username)
    except ValueError as e:
        _handle_transmission_error(e)


@router.post("/probe-verify/{transmission_id}")
def probe_unauthorized_verification(
    transmission_id: str,
    user: UserModel = Depends(require_role(["EVE", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """
    Eve attempts to invoke Bob's verification function using her adversary credentials.
    The backend RBAC and designated verifier check intercept this probe and return HTTP 403 / UNAUTHORIZED.
    """
    pkg = db.query(TransmissionPackageModel).filter(TransmissionPackageModel.id == transmission_id).first()
    if not pkg:
        raise HTTPException(status_code=404, detail="Transmission package not found")

    # Record the attack attempt
    attack_event = AttackEventModel(
        session_id=pkg.session_id,
        attack_type="UNAUTHORIZED_VERIFICATION",
        simulated=True,
        detected=True,
        payload_manipulation={"attempted_by": user.username, "legitimate_verifier": pkg.recipient_id},
        detection_evidence={
            "reason": f"Unauthorized verification probe: Actor '{user.username}' is not the designated verifier '{pkg.recipient_id}'",
            "barrier": "RBAC_VERIFIER_AUTHORIZATION"
        }
    )
    sec_event = SecurityEventModel(
        session_id=pkg.session_id,
        event_type="UNAUTHORIZED_VERIFICATION",
        severity="HIGH",
        actor=user.username,
        resource=f"/inbox/{pkg.id}/verify",
        details={"attempted_by": user.username, "recipient_id": pkg.recipient_id}
    )
    db.add(sec_event)

    audit = AuditEventModel(
        session_id=pkg.session_id,
        actor=user.username,
        event_type="UNAUTHORIZED_VERIFICATION_BLOCKED",
        details={"attempted_by": user.username, "recipient_id": pkg.recipient_id}
    )
    db.add(audit)
    db.commit()

    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "status": "BLOCKED",
            "security_verdict": "UNAUTHORIZED",
            "attack_detected": True,
            "attack_category": "UNAUTHORIZED_VERIFICATION",
            "reason": f"Access Denied: Authenticated actor '{user.username}' is not authorized to verify packages addressed to '{pkg.recipient_id}'.",
            "barrier_triggered": "Designated Verifier Authorization Barrier"
        }
    )
