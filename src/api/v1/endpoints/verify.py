"""مسار التحقق الموحد.

PAD في وضع المراقبة (monitor-only):
  - predict_liveness يُستدعى للقياس والتسجيل
  - النتيجة تُعاد في liveness_score + liveness_warning
  - لكنها لا تؤثر على القرار (لأن anti-spoof-mn3 يفشل في كشف print/replay/mask)
  - القرار يعتمد حصريًا على face matching

TODO قبل الإنتاج: استبدال PAD بـ CDCN++/DeepPixBiS وتفعيل القرار.
"""
from __future__ import annotations
import hashlib, time
from typing import Literal, Optional
import yaml
from fastapi import APIRouter
from loguru import logger
from pydantic import BaseModel, Field

router = APIRouter(tags=["verify"])
PADState = Literal["VERIFIED", "HEURISTIC", "UNAVAILABLE"]
Decision = Literal["ACCEPT", "REVIEW", "REJECT"]
_CFG = None


def _load_cfg():
    global _CFG
    if _CFG is None:
        from pathlib import Path
        for parent in Path(__file__).parents:
            candidate = parent / "config" / "thresholds.yaml"
            if candidate.exists():
                _CFG = (yaml.safe_load(candidate.read_text()) or {})
                logger.info(f"[verify] thresholds loaded from {candidate}")
                return _CFG
        _CFG = {}
        logger.warning("[verify] thresholds.yaml not found — using defaults")
    return _CFG


class VerifyRequest(BaseModel):
    selfie: str = Field(..., description="Base64 selfie")
    document: str = Field(..., description="Base64 document")
    modality: str = Field("face")


class VerifyResponse(BaseModel):
    decision: Decision
    pad_state: PADState
    face_score: Optional[float] = None
    liveness_score: Optional[float] = None
    reason: Optional[str] = None
    audit_id: Optional[str] = None
    liveness_warning: bool = False


def _record_audit(*, decision, pad_state, modality, user_hash, reason="", extras=None):
    try:
        from src.services.audit_log import log_attempt
        return log_attempt(
            status=decision.lower(), code=pad_state, reason=reason,
            detector="pad+face", user_ref=user_hash,
            extra={"modality": modality, **(extras or {})},
        )
    except Exception as exc:
        logger.warning(f"audit: {exc}")
        return None


@router.post("/", response_model=VerifyResponse)
async def verify_endpoint(payload: VerifyRequest) -> VerifyResponse:
    t0 = time.time()
    cfg = _load_cfg()
    face_accept = float(cfg.get("face_accept", cfg.get("face_similarity", 0.5668)))
    face_reject = float(cfg.get("face_reject", 0.2371))

    # ============ 1) PAD — وضع المراقبة فقط ============
    live: Optional[float] = None
    try:
        from src.pad.onnx_liveness import predict_liveness
        live = predict_liveness(payload.selfie)
        logger.info(f"[verify] PAD (monitor only) liveness={live:.3f}")
    except Exception as e:
        logger.warning(f"[verify] PAD failed: {e}")
        live = None

    # في وضع المراقبة: pad_state ثابت UNAVAILABLE، لا يؤثر على القرار
    pad_state: PADState = "UNAVAILABLE"

    # ============ 2) Face matching — يقرر النتيجة ============
    face: Optional[float] = None
    try:
        from src.pad.face_matcher import similarity
        face = similarity(payload.selfie, payload.document)
    except Exception as e:
        logger.error(f"face: {e}")

    # ============ 3) القرار (face فقط، لأن PAD في المراقبة) ============
    if face is None:
        decision = "REJECT"
        reason = "face not verifiable (fail-closed)"
    elif face >= face_accept:
        decision = "ACCEPT"
        reason = f"face={face:.3f} >= {face_accept} (PAD monitor-only)"
    elif face < face_reject:
        decision = "REJECT"
        reason = f"face={face:.3f} < {face_reject} (impostor)"
    else:
        decision = "REVIEW"
        reason = f"face={face:.3f} gray zone [{face_reject}, {face_accept})"

    # ============ 4) Audit ============
    user_hash = hashlib.sha256(payload.selfie[:32].encode()).hexdigest()[:16]
    audit_id = _record_audit(
        decision=decision, pad_state=pad_state, modality=payload.modality,
        user_hash=user_hash, reason=reason,
        extras={"live": live, "face": face, "ms": int((time.time()-t0)*1000),
                "pad_mode": "monitor_only"},
    )
    if decision == "ACCEPT" and audit_id is None:
        logger.error("ACCEPT without audit → REVIEW (fail-closed)")
        decision = "REVIEW"
        reason += " [fail-closed]"

    return VerifyResponse(
        decision=decision, pad_state=pad_state, face_score=face,
        liveness_score=live, reason=reason, audit_id=audit_id,
        liveness_warning=True,   # دائمًا في وضع المراقبة
    )
