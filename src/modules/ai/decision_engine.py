"""Decision Engine — VERIFIED / MANUAL_REVIEW / REJECTED.

Thresholds are loaded from src.core.thresholds (single source of truth).
The previous hardcoded defaults (0.40 / 0.50 / 0.45 / 0.30) were the most
lenient of all sources and could approve inputs that YAML would reject.
"""
from typing import Dict, List, Optional
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
        min_liveness: Optional[float] = None,
        min_antispoof: Optional[float] = None,
        min_face_similarity: Optional[float] = None,
        max_tampering: float = 0.60,
        min_ocr_confidence: Optional[float] = None,
    ):
        from src.core.thresholds import get_thresholds
        t = get_thresholds()

        self.verify_max_risk = verify_max_risk
        self.review_max_risk = review_max_risk
        self.max_tampering = max_tampering

        # كل العتبات من YAML ما لم تُمرَّر صراحةً (للاختبار)
        self.min_liveness = min_liveness if min_liveness is not None else t.liveness
        self.min_antispoof = min_antispoof if min_antispoof is not None else t.antispoofing
        self.min_face_similarity = (
            min_face_similarity if min_face_similarity is not None else t.face_similarity
        )
        self.min_ocr_confidence = (
            min_ocr_confidence if min_ocr_confidence is not None else t.ocr_confidence
        )

    def decide(
        self,
        risk: RiskScore,
        signals: Dict[str, float],
        reasons: List[str] | None = None,
    ) -> DecisionResult:
        reasons = reasons or []
        hard_reject = False

        liveness = signals.get("liveness")
        if liveness is not None and liveness < self.min_liveness:
            reasons.append(f"liveness ({liveness:.3f}) < {self.min_liveness}")
            hard_reject = True

        antispoof = signals.get("antispoof")
        if antispoof is not None and antispoof < self.min_antispoof:
            reasons.append(f"antispoof ({antispoof:.3f}) < {self.min_antispoof}")
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
