from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from zaslon_shared.crypto import decrypt_payload
from zaslon_shared.auth import require_roles
from zaslon_shared.schemas import DecryptRequest
from zaslon_shared.runtime import AdmissionRejected
from zaslon_shared.dispatch import sign as dispatch_sign
from zaslon_shared.job_queue import JobFailed, JobTimedOut
from .communication import read_document, read_signature, read_signing_document, safe_filename
from .identity import normalize_identity
from .verify import verify_received_document

router = APIRouter(
    prefix="/api/v1/bob",
    tags=["Bob"],
    dependencies=[Depends(require_roles("BOB"))],
)


import asyncio

@router.post("/sign")
async def sign(
    document: UploadFile = File(...),
    signer_id: str | None = Form(None),
    verifier_id: str = Form("Alice"),
    encryption_passphrase: str | None = Form(None),
    seed: int | None = Form(None),
    bit_flip: float = Form(0.0),
    phase_flip: float = Form(0.0),
    depolarizing: float = Form(0.0),
    measurement_error: float = Form(0.0),
):
    try:
        if signer_id is not None and normalize_identity(signer_id, "Bob") != "Bob":
            raise HTTPException(403, "Bob credentials cannot create another signer's signature.")
        if normalize_identity(verifier_id, "Alice") != "Alice":
            raise HTTPException(400, "Bob signatures currently authorize Alice as verifier.")
        doc_bytes = await read_signing_document(document)
        return await asyncio.to_thread(
            dispatch_sign,
            role="BOB",
            document=doc_bytes,
            parameters={
                "filename": document.filename or "document.bin",
                "signer_id": "Bob",
                "verifier_id": "Alice",
                "seed": seed,
                "encryption_passphrase": encryption_passphrase,
                "noise": {
                    "bit_flip": bit_flip,
                    "phase_flip": phase_flip,
                    "depolarizing": depolarizing,
                    "measurement_error": measurement_error,
                },
            },
        )
    except AdmissionRejected as exc:
        raise HTTPException(429, str(exc), headers={"Retry-After": "2"}) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except JobTimedOut as exc:
        raise HTTPException(202, {"job_id": exc.job_id, "status": "RUNNING"}) from exc
    except JobFailed as exc:
        raise HTTPException(503, {"job_id": exc.job_id, "code": exc.code}) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc


@router.post("/verify")
async def verify(document: UploadFile = File(...), signature: UploadFile = File(...)):
    try:
        return verify_received_document(
            document=await read_document(document),
            signature=await read_signature(signature),
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/decrypt")
def decrypt(request: DecryptRequest):
    try:
        filename, plaintext = decrypt_payload(request.encrypted_package, request.passphrase)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return Response(content=plaintext, media_type="application/octet-stream", headers={
        "Content-Disposition": f'attachment; filename="{safe_filename(filename)}"'
    })
