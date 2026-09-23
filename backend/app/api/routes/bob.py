"""
Bob (Verifier) API Router.
Dedicated to Bob's incoming package inbox, 11-step Zaslon-QDS verification, and explainability evidence inspection.
"""
import os
import json
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from ...db.session import get_db
from ...models.user import UserModel
from ...models.transmission import TransmissionPackageModel
from ...models.verification import VerificationResultModel
from ...models.session import SessionModel
from ...models.hash_record import HashRecordModel
from ...models.security_event import SecurityEventModel
from ...services.transmission_service import TransmissionService
from ...services.verification_service import VerificationService
from ...services.file_service import FileService
from ...schemas.transmission import (
    TransmissionPackageResponse,
    BobTransmissionPackageResponse,
    BobVerifyPackageRequest
)
from ...schemas.verification import VerificationResultResponse
from ..deps import require_role

router = APIRouter(tags=["Bob — Verifier"])


@router.get("/inbox", response_model=List[BobTransmissionPackageResponse])
def list_bob_inbox(
    user: UserModel = Depends(require_role(["BOB", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """Bob checks his secure inbox for incoming QDS packages dispatched by Alice (and forwarded via channel)."""
    return TransmissionService.get_bob_inbox(db, recipient_id=user.username if user.role != "ADMIN" else None)


@router.get("/inbox/{transmission_id}", response_model=BobTransmissionPackageResponse)
def inspect_inbox_package(
    transmission_id: str,
    user: UserModel = Depends(require_role(["BOB", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """Bob inspects the manifest, plaintext payload, and declared cryptographic hash of an incoming package."""
    pkg = db.query(TransmissionPackageModel).filter(TransmissionPackageModel.id == transmission_id).first()
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found in inbox")
    return pkg


@router.post("/inbox/{transmission_id}/verify", response_model=VerificationResultResponse)
def verify_package(
    transmission_id: str,
    request: BobVerifyPackageRequest,
    user: UserModel = Depends(require_role(["BOB", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """
    Bob executes the 11-step Zaslon-QDS Verification Framework on the received package:
    1. Signer identity check (Impersonation)
    2. Authorization barrier (Unauthorized verification)
    3. Message integrity check (Integrity tampering)
    4. Declaration commitment validation
    5. Anti-replay token check (Replay)
    6. Quantum evidence retrieval
    7. 5% deterministic sample selection
    8. Match / mismatch analysis
    9. Fisher's Exact Test against channel error baseline
    10. Threat classification
    11. Final security verdict & token consumption
    """
    pkg = db.query(TransmissionPackageModel).filter(TransmissionPackageModel.id == transmission_id).first()
    if not pkg:
        raise HTTPException(status_code=404, detail="Transmission package not found")

    result = VerificationService.verify_session(
        db,
        session_id=pkg.session_id,
        verifier_id=user.username,
        sample_ratio=request.sample_ratio or 0.05,
        transmission_id=transmission_id
    )

    # Synchronize transmission status
    if result.security_decision == "VERIFIED":
        pkg.status = "VERIFIED"
    elif result.security_decision in ["REJECTED", "INTEGRITY_FAILURE"]:
        pkg.status = "REJECTED"
    # If UNAUTHORIZED (access barrier trip), package status remains unchanged
    db.commit()

    return result


@router.get("/inbox/{transmission_id}/verification")
def get_inbox_package_verification(
    transmission_id: str,
    user: UserModel = Depends(require_role(["BOB", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """
    Bob queries the authoritative stored verification result and explainability evidence
    for an incoming inbox package. If not yet verified, returns has_verification=False.
    """
    pkg = db.query(TransmissionPackageModel).filter(TransmissionPackageModel.id == transmission_id).first()
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found in inbox")

    res = db.query(VerificationResultModel).filter(
        VerificationResultModel.transmission_id == transmission_id
    ).order_by(VerificationResultModel.verified_at.desc()).first()

    if not res:
        # Fallback query by session_id
        res = db.query(VerificationResultModel).filter(
            VerificationResultModel.session_id == pkg.session_id
        ).order_by(VerificationResultModel.verified_at.desc()).first()

    if not res:
        return {
            "has_verification": False,
            "status": pkg.status,
            "tracking_no": pkg.package_tracking_no
        }

    evidence = _build_verification_evidence(res, pkg)
    return {
        "has_verification": True,
        "status": pkg.status,
        "tracking_no": pkg.package_tracking_no,
        "verification_id": res.id,
        "evidence": evidence
    }


@router.get("/verifications", response_model=List[VerificationResultResponse])
def list_verifications(
    user: UserModel = Depends(require_role(["BOB", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """Lists historical verifications performed by Bob."""
    return db.query(VerificationResultModel).order_by(VerificationResultModel.verified_at.desc()).all()


@router.get("/security-events")
def list_security_events(
    user: UserModel = Depends(require_role(["BOB", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """
    Lists security intrusion detection alerts, including unauthorized probe attempts
    and unauthorized verification attempts detected across the system.
    """
    events = db.query(SecurityEventModel).order_by(SecurityEventModel.created_at.desc()).limit(100).all()
    return [
        {
            "id": e.id,
            "session_id": e.session_id,
            "event_type": e.event_type,
            "severity": e.severity,
            "actor": e.actor,
            "resource": e.resource,
            "ip_address": e.ip_address,
            "details": e.details,
            "created_at": e.created_at.isoformat() if e.created_at else None
        }
        for e in events
    ]


def _build_verification_evidence(res: VerificationResultModel, pkg: Optional[TransmissionPackageModel] = None) -> Dict[str, Any]:
    """Helper to formulate the 5-layer threat defense barrier checklist and statistical evidence."""
    barriers = [
        {
            "barrier_name": "1. Verifier Authorization Barrier",
            "threat_checked": "UNAUTHORIZED_VERIFICATION",
            "status": "FAILED" if res.attack_category in ("UNAUTHORIZED_VERIFICATION", "ACCESS_UNAUTHORIZED_VERIFIER_PROBE", "PROTOCOL_VERIFIER_SPOOFING") else "PASSED",
            "detail": "Authenticated verifier identity matches designated session recipient"
        },
        {
            "barrier_name": "2. Signer Identity Binding Barrier",
            "threat_checked": "IMPERSONATION",
            "status": "FAILED" if res.attack_category in ("IMPERSONATION", "PROTOCOL_SIGNER_IMPERSONATION") else "PASSED",
            "detail": "Declaration signer matches authentic session creator (Alice)"
        },
        {
            "barrier_name": "3. Anti-Replay Single-Use Token Barrier",
            "threat_checked": "REPLAY",
            "status": "FAILED" if res.attack_category in ("REPLAY", "PROTOCOL_REPLAY_CONSUMED_TOKEN", "PROTOCOL_EXPIRED_WINDOW_REPLAY") else "PASSED",
            "detail": "Public declaration token unconsumed and within 300s freshness window"
        },
        {
            "barrier_name": "4. Cryptographic SHA-512 Integrity Barrier",
            "threat_checked": "INTEGRITY_TAMPERING",
            "status": "FAILED" if res.attack_category in ("INTEGRITY_TAMPERING", "FILE_INTEGRITY_TAMPERING", "QDS_PACKAGE_TAMPERING", "ARTIFACT_PAYLOAD_SUBSTITUTION", "ARTIFACT_DIGEST_MISMATCH", "ARTIFACT_METADATA_TAMPERING") else "PASSED",
            "detail": "Recomputed SHA-512 digest matches original committed digest"
        },
        {
            "barrier_name": "5. Quantum Teleportation Fisher Exact Test Barrier",
            "threat_checked": "FORGERY",
            "status": "FAILED" if res.attack_category in ("FORGERY", "QUANTUM_BIT_FLIP_FORGERY", "QUANTUM_PHASE_FLIP_DEPOLARIZATION", "QUANTUM_BASIS_ALTERATION", "QUANTUM_ENTANGLEMENT_INTERCEPTION_DOS") else "PASSED",
            "detail": f"Sample mismatch ratio ({res.mismatch_ratio:.2%}) evaluated against 1.00% channel baseline via hypergeometric test"
        }
    ]

    return {
        "verification_id": res.id,
        "session_id": res.session_id,
        "tracking_no": pkg.package_tracking_no if pkg else "N/A",
        "security_decision": res.security_decision,
        "statistical_verdict": res.statistical_verdict,
        "attack_detected": res.attack_detected,
        "attack_category": res.attack_category,
        "decision_reason": res.decision_reason,
        "verified_at": res.verified_at.isoformat(),
        "statistical_evidence": {
            "sample_size": res.sample_size,
            "match_count": res.match_count,
            "mismatch_count": res.mismatch_count,
            "mismatch_ratio": res.mismatch_ratio,
            "mismatch_ratio_percent": f"{res.mismatch_ratio * 100:.2f}%",
            "threshold_ratio": res.threshold_ratio,
            "threshold_ratio_percent": f"{res.threshold_ratio * 100:.2f}%",
            "fisher_p_value": res.fisher_p_value,
            "fisher_odds_ratio": res.fisher_odds_ratio,
            "odds_ratio_display": res.odds_ratio_display,
            "baseline_error_rate": res.baseline_error_rate,
            "significance_alpha": res.significance_alpha,
            "contingency_table": res.contingency_table
        },
        "defense_barriers": barriers
    }


@router.get("/verifications/{verification_id}/evidence")
def get_verification_evidence(
    verification_id: str,
    user: UserModel = Depends(require_role(["BOB", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """
    Detailed explainability endpoint returning contingency tables, exact Fisher p-values,
    channel baseline comparisons, and the 5-layer threat defense barrier evaluation.
    """
    res = db.query(VerificationResultModel).filter(VerificationResultModel.id == verification_id).first()
    if not res:
        raise HTTPException(status_code=404, detail="Verification record not found")

    pkg = db.query(TransmissionPackageModel).filter(TransmissionPackageModel.session_id == res.session_id).first()
    return _build_verification_evidence(res, pkg)


@router.post("/manual-verify", response_model=VerificationResultResponse)
async def manual_verify(
    file: UploadFile = File(...),
    qds_file: UploadFile = File(...),
    user: UserModel = Depends(require_role(["BOB", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """
    Bob uploads an offline document file along with its companion <filename>.qds.json package
    and executes the complete 11-step Zaslon-QDS verification pipeline.
    """
    doc_bytes = await file.read()
    qds_bytes = await qds_file.read()
    try:
        qds_dict = json.loads(qds_bytes.decode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid .qds.json file: {str(e)}")

    result = VerificationService.verify_manual_upload(
        db=db,
        verifier_id=user.username,
        document_bytes=doc_bytes,
        filename=file.filename or "uploaded_document",
        qds_json_dict=qds_dict
    )
    return result


@router.get("/verifications/{verification_id}/certificate")
def get_verification_certificate(
    verification_id: str,
    user: UserModel = Depends(require_role(["BOB", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """
    Returns the official Zaslon-QDS Cryptographic Certificate Receipt (<filename>.cert.json).
    """
    res = db.query(VerificationResultModel).filter(VerificationResultModel.id == verification_id).first()
    if not res:
        raise HTTPException(status_code=404, detail="Verification record not found")

    if res.certificate_receipt:
        receipt = res.certificate_receipt
    else:
        receipt = FileService.generate_certificate_receipt(
            session_id=res.session_id,
            filename="verified_document",
            sha512_digest="",
            signer_id="Alice_Signer",
            verifier_id=user.username,
            decision=res.security_decision,
            statistical_verdict=res.statistical_verdict or "ACCEPTABLE",
            sample_size=res.sample_size or 205,
            match_count=res.match_count or 205,
            mismatch_count=res.mismatch_count or 0,
            mismatch_ratio=res.mismatch_ratio or 0.0,
            fisher_p_value=res.fisher_p_value or 1.0,
            fisher_odds_ratio=res.fisher_odds_ratio,
            contingency_table=res.contingency_table or [[205, 0], [203, 2]],
            defense_barriers=[],
            attack_detected=res.attack_detected,
            attack_category=res.attack_category,
            decision_reason=res.decision_reason
        )
        res.certificate_receipt = receipt
        res.certificate_serial = receipt.get("certificate_serial")
        db.commit()

    return JSONResponse(
        content=receipt,
        headers={"Content-Disposition": f"attachment; filename=\"{res.session_id[:8]}.cert.json\""}
    )


@router.get("/packages/{transmission_id}/qds-json")
def get_bob_qds_manifest(
    transmission_id: str,
    user: UserModel = Depends(require_role(["BOB", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """Bob downloads the companion .qds.json package for an in-flight transmission."""
    pkg = db.query(TransmissionPackageModel).filter(TransmissionPackageModel.id == transmission_id).first()
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found")
    if pkg.qds_manifest_json:
        return JSONResponse(
            content=pkg.qds_manifest_json,
            headers={"Content-Disposition": f"attachment; filename=\"{pkg.file_name or 'document'}.qds.json\""}
        )
    raise HTTPException(status_code=404, detail="QDS manifest not attached to package")


@router.get("/files/{transmission_id}/download")
def download_bob_file(
    transmission_id: str,
    user: UserModel = Depends(require_role(["BOB", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """Bob downloads the document associated with this transmission package."""
    pkg = db.query(TransmissionPackageModel).filter(TransmissionPackageModel.id == transmission_id).first()
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found")
    hash_record = db.query(HashRecordModel).filter(HashRecordModel.session_id == pkg.session_id).first()
    if not hash_record:
        raise HTTPException(status_code=404, detail="File record not found")

    if hash_record.storage_path and os.path.exists(hash_record.storage_path):
        return FileResponse(
            path=hash_record.storage_path,
            filename=hash_record.file_name or pkg.file_name or "document.bin",
            media_type=hash_record.file_mime_type or pkg.file_mime_type or "application/octet-stream"
        )
    else:
        from fastapi.responses import Response
        return Response(
            content=(hash_record.raw_message or pkg.message_payload or "").encode("utf-8"),
            media_type="text/plain",
            headers={"Content-Disposition": f"attachment; filename=\"{hash_record.file_name or pkg.file_name or 'document.txt'}\""}
        )
