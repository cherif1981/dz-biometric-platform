"""مسار التحقق الموحد.

PAD عبر src.pad.service (خدمة موثقة تُصدر قرارًا أمنيًا):
  - get_pad_service().evaluate() يُنتج PADResult (decision + state)
  - لا يمكن إصدار ACCEPT بدون PAD VERIFIED + face مقبول
  - UNAVAILABLE → REJECT (fail-closed, no model)
  - HEURISTIC / LOADED → REVIEW (fail-closed, unverified model)
  - PAD REJECT → REJECT (هجوم مؤكد)
"""
from __future__ import annotations

import base64
import hashlib
import time
from typing import Literal, Optional

import numpy as np
import yaml
from fastapi import APIRouter
from loguru import logger
from pydantic import BaseModel, Field

router = APIRouter(tags=["verify"])
PADState = Literal["VERIFIED", "LOADED", "HEURISTIC", "UNAVAILABLE"]
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


def _decode_base64_image(b64: str):
    """base64 → BGR numpy. None عند الفشل."""
    try:
        img_bytes = base64.b64decode(b64)
        arr = np.frombuffer(img_bytes, np.uint8)
        try:
            import cv2
            return cv2.imdecode(arr, cv2.IMREAD_COLOR)
        except ImportError:
            import io

            from PIL import Image
            img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            return np.array(img)[:, :, ::-1]
    except Exception as e:
        logger.warning(f"[verify] selfie decode failed: {e}")
        return None


def _evaluate_pad(selfie_b64: str, request_id: str):
    """يستدعي الخدمة الموثقة. (decision, state_str, liveness, reasons)."""
    try:
        from src.pad.contract import PADInput
        from src.pad.service import get_pad_service
    except Exception as e:
        return None, "UNAVAILABLE", None, (f"import failed: {e}",)

    image_bgr = _decode_base64_image(selfie_b64)
    if image_bgr is None:
        return None, "UNAVAILABLE", None, ("selfie decode failed",)

    try:
        inp = PADInput(image_bgr=image_bgr, request_id=request_id, source="verify_api")
        result = get_pad_service().evaluate(inp)
        return (result.decision, result.state.value, result.liveness, result.reasons)
    except Exception as e:
        logger.error(f"[verify] PAD evaluate failed: {e}")
        return None, "UNAVAILABLE", None, (f"evaluate failed: {e}",)


@router.post("/", response_model=VerifyResponse)
async def verify_endpoint(payload: VerifyRequest) -> VerifyResponse:
    t0 = time.time()
    cfg = _load_cfg()
    face_accept = float(cfg.get("face_accept", cfg.get("face_similarity", 0.5668)))
    face_reject = float(cfg.get("face_reject", 0.2371))

    user_hash = hashlib.sha256(payload.selfie[:32].encode()).hexdigest()[:16]
    request_id = f"{user_hash}-{int(t0 * 1000)}"

    # ============ 1) PAD عبر الخدمة الموحدة ============
    pad_decision, pad_state, liveness, pad_reasons = _evaluate_pad(payload.selfie, request_id)
    logger.info(
        f"[verify] PAD state={pad_state} decision={pad_decision} "
        f"reasons={pad_reasons[:2] if pad_reasons else ()}"
    )

    # ============ 2) Face matching ============
    face: Optional[float] = None
    try:
        from src.pad.face_matcher import similarity
        face = similarity(payload.selfie, payload.document)
    except Exception as e:
        logger.error(f"face: {e}")

    # ============ 3) قرار مركّب — PAD أولًا، face ثانيًا ============
    from src.pad.contract import Decision as PADDecision

    if pad_decision is None:
        decision = "REVIEW"
        reason = f"PAD unavailable ({pad_reasons[0] if pad_reasons else 'unknown'}) → review (fail-closed)"
    elif pad_decision == PADDecision.REJECT:
        decision = "REJECT"
        reason = f"PAD reject: {pad_reasons[0] if pad_reasons else 'attack detected'}"
    elif pad_decision == PADDecision.REVIEW:
        decision = "REVIEW"
        reason = f"PAD review: {pad_reasons[0] if pad_reasons else 'uncertain'}"
    elif pad_decision == PADDecision.ACCEPT:
        if face is None:
            decision = "REJECT"
            reason = "face not verifiable (fail-closed)"
        elif face >= face_accept:
            decision = "ACCEPT"
            reason = f"PAD verified + face={face:.3f} >= {face_accept}"
        elif face < face_reject:
            decision = "REJECT"
            reason = f"PAD verified but face={face:.3f} < {face_reject} (impostor)"
        else:
            decision = "REVIEW"
            reason = f"PAD verified but face={face:.3f} in gray zone [{face_reject}, {face_accept})"
    else:
        decision = "REVIEW"
        reason = f"unexpected PAD decision: {pad_decision}"

    # ============ 4) Audit + حماية fail-closed إضافية ============
    audit_id = _record_audit(
        decision=decision, pad_state=pad_state, modality=payload.modality,
        user_hash=user_hash, reason=reason,
        extras={"live": liveness, "face": face, "ms": int((time.time()-t0)*1000),
                "pad_reasons": list(pad_reasons or [])},
    )
    if decision == "ACCEPT" and audit_id is None:
        logger.error("ACCEPT without audit → REVIEW (fail-closed)")
        decision = "REVIEW"
        reason += " [fail-closed]"

    return VerifyResponse(
        decision=decision, pad_state=pad_state, face_score=face,
        liveness_score=liveness, reason=reason, audit_id=audit_id,
        liveness_warning=(pad_state != "VERIFIED"),
    )
