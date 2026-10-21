from fastapi import APIRouter, UploadFile, File, Form, Request, Depends
from typing import Optional
from src.services.verification_service import VerificationEngine
from src.core.rate_limit import limiter
from src.core.permissions import RequireScopes

router = APIRouter(prefix="/verify", tags=["verification"])
_engine = None

def _get_engine():
    global _engine
    if _engine is None:
        _engine = VerificationEngine()
    return _engine



@router.post("/")
@limiter.limit("10/minute")
async def verify_identity(
    request: Request,
    id_image: UploadFile = File(...),
    selfie: UploadFile = File(...),
    full_name: Optional[str] = Form(None),
    nin: Optional[str] = Form(None),
    _: dict = Depends(RequireScopes("write")),
):
    ib = await id_image.read()
    sb = await selfie.read()
    exp = {}
    if full_name:
        exp["full_name"] = full_name
    if nin:
        exp["nin"] = nin
    r = _get_engine().verify(ib, sb, exp or None, client_ip=request.client.host)
    return {"status": r.status.value, "confidence": r.confidence,
            "face_similarity": r.face_similarity, "liveness_score": r.liveness_score,
            "antispoof_score": r.antispoof_score, "ocr_fields": r.ocr_fields,
            "reasons": r.reasons, "scores": r.scores, "audit_id": r.audit_id}
