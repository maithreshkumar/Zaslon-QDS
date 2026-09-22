"""
Alice (Signer) API Router.
Dedicated to Alice's signing, teleportation orchestration, and package dispatch workflows.
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os

from ...db.session import get_db
from ...models.user import UserModel
from ...models.session import SessionModel
from ...models.hash_record import HashRecordModel
from ...models.transmission import TransmissionPackageModel
from ...models.participant import ParticipantModel
from ...models.declaration import PublicDeclarationModel
from ...models.quantum_run import QuantumRunModel
from ...services.hashing_service import HashingService
from ...services.teleportation_service import TeleportationService
from ...services.declaration_service import DeclarationService
from ...services.transmission_service import TransmissionService
from ...services.file_service import FileService
from ...schemas.transmission import (
    AliceDraftRequest,
    AliceSignResponse,
    TransmissionPackageResponse
)
from ..deps import require_role

router = APIRouter(tags=["Alice — Signer"])


@router.post("/upload")
async def upload_document_or_directive(
    file: Optional[UploadFile] = File(None),
    document_title: str = Form("Security Directive"),
    recipient_id: str = Form("Bob_Verifier"),
    directive_text: Optional[str] = Form(None),
    user: UserModel = Depends(require_role(["ALICE", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """Alice uploads any document file (PDF, TXT, DOCX, JSON, bin) or types directive text."""
    session = SessionModel(
        session_name=document_title,
        created_by=user.username,
        verifier_id=recipient_id or "Bob_Verifier",
        status="CREATED"
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Automatically add Alice as Signer participant
    alice_p = ParticipantModel(
        session_id=session.id,
        name=user.username,
        role="Signer",
        public_key_fingerprint="alice_fp_sha512_qds_key",
        auth_token_hash="alice_auth_hash"
    )
    # Add Bob as Verifier participant
    bob_p = ParticipantModel(
        session_id=session.id,
        name=session.verifier_id,
        role="Verifier",
        public_key_fingerprint="bob_fp_sha512_qds_key",
        auth_token_hash="bob_auth_hash"
    )
    db.add(alice_p)
    db.add(bob_p)
    db.commit()

    if file:
        file_meta = await FileService.stream_and_hash_upload(
            session_id=session.id,
            filename=file.filename or "document.bin",
            upload_file=file,
            mime_type=file.content_type
        )
        hash_record = HashRecordModel(
            session_id=session.id,
            raw_message=f"[BINARY FILE: {file_meta['filename']}]",
            message_bytes_len=file_meta["file_size_bytes"],
            sha512_digest=file_meta["sha512_digest"],
            hash_encoding_format="hex",
            file_name=file_meta["filename"],
            file_mime_type=file_meta["mime_type"],
            file_size_bytes=file_meta["file_size_bytes"],
            storage_path=file_meta["storage_path"],
            is_binary_file=True
        )
        db.add(hash_record)
        session.status = "HASHED"
        db.commit()
        db.refresh(hash_record)

        return {
            "session_id": session.id,
            "document_title": session.session_name,
            "recipient_id": session.verifier_id,
            "file_name": file_meta["filename"],
            "file_size_bytes": file_meta["file_size_bytes"],
            "mime_type": file_meta["mime_type"],
            "sha512_digest": file_meta["sha512_digest"],
            "status": session.status,
            "is_file": True
        }
    else:
        text_payload = directive_text or "NATIONAL CRITICAL INFRASTRUCTURE DEFENSE DIRECTIVE #26141"
        hash_record = HashingService.process_message_hash(db, session.id, text_payload, user.username)
        hash_record.file_name = f"{document_title.replace(' ', '_')}.txt"
        hash_record.file_mime_type = "text/plain"
        hash_record.file_size_bytes = len(text_payload.encode())
        db.commit()
        return {
            "session_id": session.id,
            "document_title": session.session_name,
            "recipient_id": session.verifier_id,
            "file_name": hash_record.file_name,
            "file_size_bytes": hash_record.file_size_bytes,
            "mime_type": "text/plain",
            "sha512_digest": hash_record.sha512_digest,
            "status": session.status,
            "is_file": False
        }


@router.post("/draft")
def create_draft(
    request: AliceDraftRequest,
    user: UserModel = Depends(require_role(["ALICE", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """Alice creates a new signing draft with message payload and recipient selection."""
    session = SessionModel(
        session_name=request.document_title,
        created_by=user.username,
        verifier_id=request.recipient_id or "Bob_Verifier",
        status="CREATED"
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Automatically add Alice as Signer participant
    alice_p = ParticipantModel(
        session_id=session.id,
        name=user.username,
        role="Signer",
        public_key_fingerprint="alice_fp_sha512_qds_key",
        auth_token_hash="alice_auth_hash"
    )
    # Add Bob as Verifier participant
    bob_p = ParticipantModel(
        session_id=session.id,
        name=session.verifier_id,
        role="Verifier",
        public_key_fingerprint="bob_fp_sha512_qds_key",
        auth_token_hash="bob_auth_hash"
    )
    db.add(alice_p)
    db.add(bob_p)
    db.commit()

    # Compute canonical SHA-512 digest
    hash_record = HashingService.process_message_hash(db, session.id, request.message_payload, user.username)
    hash_record.file_name = f"{request.document_title.replace(' ', '_')}.txt"
    hash_record.file_mime_type = "text/plain"
    hash_record.file_size_bytes = len(request.message_payload.encode())
    db.commit()

    return {
        "session_id": session.id,
        "document_title": session.session_name,
        "recipient_id": session.verifier_id,
        "file_name": hash_record.file_name,
        "file_size_bytes": hash_record.file_size_bytes,
        "sha512_digest": hash_record.sha512_digest,
        "status": session.status
    }


@router.post("/sessions/{session_id}/sign", response_model=AliceSignResponse)
def sign_session(
    session_id: str,
    user: UserModel = Depends(require_role(["ALICE", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """Alice executes 4,096 CUDA-Q teleportation operations and seals the public declaration."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Check if session is already signed (idempotent signature)
    declaration = db.query(PublicDeclarationModel).filter(PublicDeclarationModel.session_id == session_id).first()
    run = db.query(QuantumRunModel).filter(QuantumRunModel.session_id == session_id).order_by(QuantumRunModel.created_at.desc()).first()
    hash_record = db.query(HashRecordModel).filter(HashRecordModel.session_id == session_id).first()

    if declaration and run:
        filename = hash_record.file_name if hash_record else "document.txt"
        file_size = hash_record.file_size_bytes if hash_record else (hash_record.message_bytes_len if hash_record else 0)
        mime = hash_record.file_mime_type if hash_record else "text/plain"

        qds_manifest = FileService.build_qds_json_manifest(
            package_tracking_no=f"QDS-PKG-{session.id[:8].upper()}",
            session_id=session.id,
            filename=filename,
            file_size_bytes=file_size,
            mime_type=mime,
            sha512_digest=hash_record.sha512_digest if hash_record else "",
            signer_id=declaration.signer_id,
            verifier_id=session.verifier_id,
            declaration_id=declaration.id,
            signature_token=declaration.signature_token,
            declaration_payload_hash=declaration.declaration_payload_hash,
            quantum_run_id=run.id,
            teleportation_count=run.teleportation_count,
            declared_at=declaration.declared_at
        )

        return AliceSignResponse(
            session_id=session.id,
            sha512_digest=hash_record.sha512_digest if hash_record else "",
            total_operations=run.teleportation_count,
            completed_operations=run.completed_operations,
            duration_ms=run.execution_duration_ms or 0.0,
            signature_token=declaration.signature_token,
            status=session.status,
            file_name=filename,
            file_size_bytes=file_size,
            qds_manifest_json=qds_manifest
        )

    # 1. Execute 4,096 Teleportation circuits on NVIDIA CUDA-Q
    run = TeleportationService.launch_teleportation(db, session_id, actor=user.username, background=False)

    # 2. Issue public declaration commitment token
    declaration = DeclarationService.create_declaration(db, session_id, signer_id=user.username)

    # Pre-build .qds.json package
    filename = hash_record.file_name if hash_record else "document.txt"
    file_size = hash_record.file_size_bytes if hash_record else (hash_record.message_bytes_len if hash_record else 0)
    mime = hash_record.file_mime_type if hash_record else "text/plain"

    qds_manifest = FileService.build_qds_json_manifest(
        package_tracking_no=f"QDS-PKG-{session.id[:8].upper()}",
        session_id=session.id,
        filename=filename,
        file_size_bytes=file_size,
        mime_type=mime,
        sha512_digest=hash_record.sha512_digest if hash_record else "",
        signer_id=user.username,
        verifier_id=session.verifier_id,
        declaration_id=declaration.id,
        signature_token=declaration.signature_token,
        declaration_payload_hash=declaration.declaration_payload_hash,
        quantum_run_id=run.id,
        teleportation_count=run.teleportation_count,
        declared_at=declaration.declared_at
    )

    return AliceSignResponse(
        session_id=session.id,
        sha512_digest=hash_record.sha512_digest if hash_record else "",
        total_operations=run.teleportation_count,
        completed_operations=run.completed_operations,
        duration_ms=run.execution_duration_ms or 0.0,
        signature_token=declaration.signature_token,
        status=session.status,
        file_name=filename,
        file_size_bytes=file_size,
        qds_manifest_json=qds_manifest
    )


@router.get("/packages/{session_id}/qds-json")
def export_qds_json(
    session_id: str,
    user: UserModel = Depends(require_role(["ALICE", "ADMIN", "BOB", "EVE"])),
    db: Session = Depends(get_db)
):
    """Exports or downloads the standardized <filename>.qds.json cryptographic signature bundle."""
    pkg = db.query(TransmissionPackageModel).filter(TransmissionPackageModel.session_id == session_id).first()
    if pkg and pkg.qds_manifest_json:
        return JSONResponse(
            content=pkg.qds_manifest_json,
            headers={"Content-Disposition": f"attachment; filename=\"{pkg.file_name or 'document'}.qds.json\""}
        )

    # If package not yet dispatched, build on the fly from session declaration
    declaration = db.query(PublicDeclarationModel).filter(PublicDeclarationModel.session_id == session_id).first()
    hash_record = db.query(HashRecordModel).filter(HashRecordModel.session_id == session_id).first()
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not declaration or not hash_record or not session:
        raise HTTPException(status_code=404, detail="QDS manifest not yet ready. Sign document first.")

    qrun = db.query(QuantumRunModel).filter(QuantumRunModel.session_id == session_id).first()
    manifest = FileService.build_qds_json_manifest(
        package_tracking_no=f"QDS-PKG-{session.id[:8].upper()}",
        session_id=session.id,
        filename=hash_record.file_name or "document.txt",
        file_size_bytes=hash_record.file_size_bytes or hash_record.message_bytes_len,
        mime_type=hash_record.file_mime_type or "text/plain",
        sha512_digest=hash_record.sha512_digest,
        signer_id=declaration.signer_id,
        verifier_id=session.verifier_id,
        declaration_id=declaration.id,
        signature_token=declaration.signature_token,
        declaration_payload_hash=declaration.declaration_payload_hash,
        quantum_run_id=qrun.id if qrun else "simulated_run",
        declared_at=declaration.declared_at
    )
    return JSONResponse(
        content=manifest,
        headers={"Content-Disposition": f"attachment; filename=\"{hash_record.file_name or 'document'}.qds.json\""}
    )


@router.get("/files/{session_id}/download")
def download_file(
    session_id: str,
    user: UserModel = Depends(require_role(["ALICE", "ADMIN", "BOB", "EVE"])),
    db: Session = Depends(get_db)
):
    """Downloads the original document file signed in this session."""
    hash_record = db.query(HashRecordModel).filter(HashRecordModel.session_id == session_id).first()
    if not hash_record:
        raise HTTPException(status_code=404, detail="File record not found")

    if hash_record.storage_path and os.path.exists(hash_record.storage_path):
        return FileResponse(
            path=hash_record.storage_path,
            filename=hash_record.file_name or "document.bin",
            media_type=hash_record.file_mime_type or "application/octet-stream"
        )
    else:
        from fastapi.responses import Response
        return Response(
            content=hash_record.raw_message.encode("utf-8"),
            media_type="text/plain",
            headers={"Content-Disposition": f"attachment; filename=\"{hash_record.file_name or 'directive.txt'}\""}
        )


@router.post("/packages/{session_id}/dispatch", response_model=TransmissionPackageResponse)
def dispatch_package(
    session_id: str,
    user: UserModel = Depends(require_role(["ALICE", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """Alice seals the signed package and dispatches it into the transmission channel (IN_TRANSIT)."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    pkg = TransmissionService.dispatch_package(
        db,
        session_id=session_id,
        sender_id=user.username,
        recipient_id=session.verifier_id
    )
    return pkg


@router.get("/packages", response_model=List[TransmissionPackageResponse])
def list_alice_packages(
    user: UserModel = Depends(require_role(["ALICE", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """Lists all packages created and signed by Alice."""
    packages = db.query(TransmissionPackageModel).filter(
        (TransmissionPackageModel.sender_id == user.username) | (user.role == "ADMIN")
    ).order_by(TransmissionPackageModel.created_at.desc()).all()
    return packages


@router.get("/packages/{transmission_id}", response_model=TransmissionPackageResponse)
def get_alice_package(
    transmission_id: str,
    user: UserModel = Depends(require_role(["ALICE", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """Inspects a specific package signed by Alice."""
    pkg = db.query(TransmissionPackageModel).filter(TransmissionPackageModel.id == transmission_id).first()
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found")
    return pkg


@router.get("/recipients")
def list_recipients(
    user: UserModel = Depends(require_role(["ALICE", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """Lists eligible Bob verifiers in the network."""
    bob_users = db.query(UserModel).filter(UserModel.role == "BOB").all()
    recipients = [
        {"id": u.username, "name": u.public_identity, "status": "ONLINE"}
        for u in bob_users
    ]
    if not recipients:
        recipients = [
            {"id": "Bob_Verifier", "name": "Bob (Branch Verifier)", "status": "ONLINE"}
        ]
    return recipients
