"""واجهة توافق: تفوّض إلى UnifiedDecisionEngine مع إسقاط مفاهيم المخاطر على العتبات.

المعاملات القديمة (review_max_risk, max_tampering, …) تُحوّل إلى عتبات مكافئة:
  face_similarity   = 1 - review_max_risk   (كلما قلّت المخاطرة زادت العتبة)
  antispoof         = 1 - max_tampering
  liveness          = liveness_threshold (أو الافتراضي)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ...core.decision_policy import (
    UnifiedDecisionEngine, DecisionThresholds, CriterionThreshold,
    DecisionResult, Decision, CriterionStatus,
)

__all__ = ["AIDecisionEngine", "DecisionResult", "Decision", "CriterionStatus"]


@dataclass
class AIDecisionEngine:
    review_max_risk: float = 0.65
    max_tampering: float = 0.60
    liveness_threshold: float = 0.80
    ocr_threshold: float = 0.70

    def __post_init__(self):
        # نحوّل «المخاطر» إلى عتبات قبول مكافئة، ونبقي نطاق مراجعة نسبي 0.9
        t = DecisionThresholds(
            face_similarity=CriterionThreshold(
                "face_similarity", accept=round(1 - self.review_max_risk, 6),
                review_factor=0.9, critical=True),
            liveness=CriterionThreshold(
                "liveness", accept=self.liveness_threshold, review_factor=0.85, critical=True),
            antispoof=CriterionThreshold(
                "antispoof", accept=round(1 - self.max_tampering, 6),
                review_factor=0.85, critical=True),
            ocr_confidence=CriterionThreshold(
                "ocr_confidence", accept=self.ocr_threshold, review_factor=0.75, critical=False),
        )
        self._engine = UnifiedDecisionEngine(t)
        self.last_result: Optional[DecisionResult] = None

    def decide(self, scores: dict) -> DecisionResult:
        self.last_result = self._engine.decide(scores)
        return self.last_result
