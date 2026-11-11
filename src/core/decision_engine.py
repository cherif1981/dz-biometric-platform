from __future__ import annotations

from dataclasses import dataclass

from src.pad.contract import Decision as PADDecision
from src.pad.contract import PADInput, PADResult
from src.pad.service import get_pad_service


@dataclass
class DecisionResult:
    decision: PADDecision
    pad: PADResult
    reasons: tuple[str, ...]


class DecisionEngine:
    """منسّق القرار. لا يحسب PAD — يستقبله من src.pad.service."""

    def evaluate(
        self,
        image_bgr,
        *,
        request_id: str,
        source: str,
        face_similarity: float,
        ocr_confidence: float,
        policy,
    ) -> DecisionResult:
        pad = get_pad_service().evaluate(
            PADInput(image_bgr=image_bgr, request_id=request_id, source=source))

        # REJECT من PAD يوقف كل شيء
        if pad.decision == PADDecision.REJECT:
            return DecisionResult(PADDecision.REJECT, pad, pad.reasons)

        # REVIEW من PAD يمنع ACCEPT مهما كانت بقية المعايير
        if pad.decision == PADDecision.REVIEW:
            return DecisionResult(PADDecision.REVIEW, pad, pad.reasons)

        # ACCEPT من PAD فقط: نكمل للمعايير الأخرى
        if policy is None:
            return DecisionResult(PADDecision.ACCEPT, pad, pad.reasons)
        other = policy.evaluate(
            {"face_similarity": face_similarity, "ocr_confidence": ocr_confidence},
            pad_result=pad,
        )
        return DecisionResult(other, pad, pad.reasons)
