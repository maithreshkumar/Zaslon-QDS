from __future__ import annotations

import json
from pathlib import Path
import re

from fastapi import HTTPException, UploadFile
from pydantic import ValidationError

from .config import settings
from .schemas import SignatureArtifact


async def read_limited(upload: UploadFile, maximum: int, label: str) -> bytes:
    payload = await upload.read(maximum + 1)
    if len(payload) > maximum:
        raise HTTPException(413, f"{label} exceeds the configured size limit")
    if not payload:
        raise HTTPException(400, f"{label} is empty")
    return payload


async def read_document(upload: UploadFile) -> bytes:
    return await read_limited(upload, settings.max_document_bytes, "Document")


async def read_signing_document(upload: UploadFile) -> bytes:
    """Read source bytes and reject accidental re-signing of a QDS artifact."""

    payload = await read_document(upload)
    if (upload.filename or "").lower().endswith(".qds.json"):
        try:
            candidate = json.loads(payload.decode("utf-8"))
            SignatureArtifact.model_validate(candidate)
        except (UnicodeDecodeError, json.JSONDecodeError, ValidationError):
            return payload
        raise HTTPException(
            400,
            "A .qds.json signature artifact cannot be used as Alice/Bob's source "
            "document. Open the verifier page and upload the original document "
            "plus this signature artifact separately.",
        )
    return payload


async def read_signature(upload: UploadFile) -> dict:
    raw = await read_limited(upload, settings.max_signature_bytes, "Signature")
    try:
        parsed = json.loads(raw.decode("utf-8"))
        return SignatureArtifact.model_validate(parsed).model_dump()
    except (UnicodeDecodeError, json.JSONDecodeError, ValidationError) as exc:
        raise HTTPException(400, "Signature must be valid UTF-8 JSON matching the QDS schema") from exc


def safe_filename(filename: str) -> str:
    name = Path(filename).name
    return re.sub(r"[^A-Za-z0-9._-]", "_", name)[:200] or "document.bin"
