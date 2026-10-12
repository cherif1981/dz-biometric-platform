from fastapi import APIRouter, UploadFile, File, Form, Request, Depends
from typing import Optional

from src.core.security import get_current_user
from src.core.upload_limits import (
    MAX_UPLOAD_BYTES,
    read_limited,
    validate_image_bytes,
)
from src.services.verification_service import VerificationEngine

router = APIRouter(
    prefix="/verify",
    tags=["verification"],
    dependencies=[Depends(get_current_user)],
)

engine = VerificationEngine()


@router.post("/")
async def verify_identity(
    request: Request,
    id_image: UploadFile = File(...),
    selfie: UploadFile = File(...),
    full_name: Optional[str] = Form(None),
    nin: Optional[str] = Form(None),
):
    # SEC-07: hard limit per file + magic-byte + dimension check
    ib = await read_limited(id_image, MAX_UPLOAD_BYTES)
    sb = await read_limited(selfie, MAX_UPLOAD_BYTES)
    validate_image_bytes(ib)
    validate_image_bytes(sb)

    exp = {}
    if full_name:
        exp["full_name"] = full_name
    if nin:
        exp["nin"] = nin

    r = engine.verify(ib, sb, exp or None, client_ip=request.client.host)
    return {
        "status": r.status.value,
        "confidence": r.confidence,
        "face_similarity": r.face_similarity,
        "liveness_score": r.liveness_score,
        "antispoof_score": r.antispoof_score,
        "ocr_fields": r.ocr_fields,
        "reasons": r.reasons,
        "scores": r.scores,
        "audit_id": r.audit_id,
    }
