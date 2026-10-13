"""Decision Engine — VERIFIED / MANUAL_REVIEW / REJECTED."""

from typing import Dict, List
from loguru import logger

from .models import Decision, DecisionResult, RiskScore, RiskLevel


class DecisionEngine:
    """
    يحول RiskScore + الإشارات الخام إلى قرار نهائي.
    يستخدم عتبات صارمة للإشارات الحرجة (liveness، tampering)
    قبل الاعتماد على risk_score الإجمالي.
    """

    def __init__(
        self,
        verify_max_risk: float = 0.30,
        review_max_risk: float = 0.65,
        min_liveness: float = 0.50,
        min_antispoof: float = 0.45,
        min_face_similarity: float = 0.40,
        max_tampering: float = 0.60,
        min_ocr_confidence: float = 0.30,
    ):
        self.verify_max_risk = verify_max_risk
        self.review_max_risk = review_max_risk
        self.min_liveness = min_liveness
        self.min_antispoof = min_antispoof
        self.min_face_similarity = min_face_similarity
        self.max_tampering = max_tampering
        self.min_ocr_confidence = min_ocr_confidence

    def decide(
        self,
        risk: RiskScore,
        signals: Dict[str, float],
        reasons: List[str] | None = None,
    ) -> DecisionResult:
        reasons = reasons or []

        # --- قواعد رفض صارمة (Hard Reject) ---
        hard_reject = False

        liveness = signals.get("liveness")
        if liveness is not None and liveness < self.min_liveness:
            reasons.append(
                f"liveness ({liveness:.3f}) < {self.min_liveness}"
            )
            hard_reject = True

        antispoof = signals.get("antispoof")
        if antispoof is not None and antispoof < self.min_antispoof:
            reasons.append(
                f"antispoof ({antispoof:.3f}) < {self.min_antispoof}"
            )
            hard_reject = True

        similarity = signals.get("face_similarity")
        if similarity is not None and similarity < self.min_face_similarity:
            reasons.append(
                f"face_similarity ({similarity:.3f}) < {self.min_face_similarity}"
            )
            hard_reject = True

        tampering = signals.get("document_tampering")
        if tampering is not None and tampering > self.max_tampering:
            reasons.append(
                f"document_tampering ({tampering:.3f}) > {self.max_tampering}"
            )
            hard_reject = True

        if hard_reject:
            logger.warning(f"REJECTED بسبب: {reasons}")
            return DecisionResult(
                decision=Decision.REJECTED,
                risk=risk,
                reasons=reasons,
                raw_scores=signals,
            )

        # --- قرار بناءً على risk_score ---
        if risk.score <= self.verify_max_risk:
            decision = Decision.VERIFIED
        elif risk.score <= self.review_max_risk:
            decision = Decision.MANUAL_REVIEW
            reasons.append(f"risk_score ({risk.score:.3f}) في نطاق المراجعة")
        else:
            decision = Decision.REJECTED
            reasons.append(f"risk_score ({risk.score:.3f}) مرتفع جدًا")

        logger.info(f"القرار: {decision.value} | risk={risk.score:.3f}")
        return DecisionResult(
            decision=decision,
            risk=risk,
            reasons=reasons,
            raw_scores=signals,
        )
