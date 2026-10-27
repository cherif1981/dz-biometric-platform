"""
سياسة القرار الموحدة (v1.1.0).

تمثّل هذه السياسة نمطي القرار الموجودين في المستودع:
  - عتبات مطلقة (accept / review)  → تعبّر عن core/decision_engine السابق
  - نطاق مراجعة نسبي (review_factor) → تعبّر عن `thresholds[m] * 0.9`

قواعد الدمج (بدون متوسطات):
  1) فشل معيار حرج                 → REJECT
  2) معيار حرج في نطاق المراجعة    → MANUAL_REVIEW
  3) فشل/غياب معيار غير حرج        → MANUAL_REVIEW
  4) كل المعايير الحرجة PASS        → ACCEPT
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)
POLICY_VERSION = "1.1.0"


class Decision(str, Enum):
    ACCEPT = "ACCEPT"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    REJECT = "REJECT"


class CriterionStatus(str, Enum):
    PASS = "PASS"
    REVIEW = "REVIEW"
    FAIL = "FAIL"


@dataclass(frozen=True)
class CriterionThreshold:
    """عتبة معيار واحد.

    accept        : الحد الأدنى للنجاح (PASS إن كان score >= accept)
    review        : الحد الأدنى للمراجعة (REVIEW إن كان review <= score < accept)
    review_factor : بديل نسبي؛ إن كانت review=None فـ review = accept * review_factor
    critical      : هل فشل المعيار يوجب الرفض مباشرة (بدل المراجعة)
    """
    name: str
    accept: float
    review: Optional[float] = None
    review_factor: float = 0.9
    critical: bool = True

    def __post_init__(self):
        if self.review is None:
            object.__setattr__(self, "review", round(self.accept * self.review_factor, 6))
        if not 0.0 <= self.review <= self.accept <= 1.0:
            raise ValueError(
                f"{self.name}: review={self.review} يجب أن يكون 0 ≤ review ≤ accept ≤ 1"
            )

    def evaluate(self, score: float) -> CriterionStatus:
        if score >= self.accept:
            return CriterionStatus.PASS
        if score >= self.review:
            return CriterionStatus.REVIEW
        return CriterionStatus.FAIL


@dataclass(frozen=True)
class DecisionThresholds:
    face_similarity: CriterionThreshold = field(
        default_factory=lambda: CriterionThreshold("face_similarity", 0.75, review_factor=0.9, critical=True))
    liveness: CriterionThreshold = field(
        default_factory=lambda: CriterionThreshold("liveness", 0.80, review_factor=0.85, critical=True))
    antispoof: CriterionThreshold = field(
        default_factory=lambda: CriterionThreshold("antispoof", 0.80, review_factor=0.85, critical=True))
    ocr_confidence: CriterionThreshold = field(
        default_factory=lambda: CriterionThreshold("ocr_confidence", 0.70, review_factor=0.75, critical=False))

    def to_dict(self) -> dict:
        return {n: asdict(getattr(self, n)) for n in
                ("face_similarity", "liveness", "antispoof", "ocr_confidence")}

    @classmethod
    def from_settings(cls, settings=None) -> "DecisionThresholds":
        g = lambda k, d: getattr(settings, k, d) if settings is not None else d
        return cls(
            face_similarity=CriterionThreshold(
                "face_similarity", g("FACE_THRESHOLD", 0.75),
                review_factor=g("FACE_REVIEW_FACTOR", 0.9), critical=True),
            liveness=CriterionThreshold(
                "liveness", g("LIVENESS_THRESHOLD", 0.80),
                review_factor=g("LIVENESS_REVIEW_FACTOR", 0.85), critical=True),
            antispoof=CriterionThreshold(
                "antispoof", g("ANTISPOOF_THRESHOLD", 0.80),
                review_factor=g("ANTISPOOF_REVIEW_FACTOR", 0.85), critical=True),
            ocr_confidence=CriterionThreshold(
                "ocr_confidence", g("OCR_THRESHOLD", 0.70),
                review_factor=g("OCR_REVIEW_FACTOR", 0.75), critical=False),
        )


@dataclass
class CriterionResult:
    name: str
    score: Optional[float]
    status: CriterionStatus
    accept_threshold: float
    review_threshold: float
    critical: bool
    error: Optional[str] = None


@dataclass
class DecisionResult:
    decision: Decision
    reasons: list[str]
    criteria: list[CriterionResult]
    policy_version: str
    thresholds_snapshot: dict
    scores_raw: dict

    def to_dict(self) -> dict:
        return {
            "decision": self.decision.value,
            "reasons": self.reasons,
            "policy_version": self.policy_version,
            "thresholds_snapshot": self.thresholds_snapshot,
            "scores_raw": self.scores_raw,
            "criteria": [
                {"name": c.name, "score": c.score, "status": c.status.value,
                 "accept_threshold": c.accept_threshold,
                 "review_threshold": c.review_threshold,
                 "critical": c.critical, "error": c.error}
                for c in self.criteria
            ],
        }


class UnifiedDecisionEngine:
    def __init__(self, thresholds: DecisionThresholds, strict_critical: bool = True):
        self.thresholds = thresholds
        self.strict_critical = strict_critical

    def decide(self, scores: dict, request_id: Optional[str] = None) -> DecisionResult:
        criteria, reasons = [], []
        has_review = has_critical_fail = False

        for name, t in (
            ("face_similarity", self.thresholds.face_similarity),
            ("liveness", self.thresholds.liveness),
            ("antispoof", self.thresholds.antispoof),
            ("ocr_confidence", self.thresholds.ocr_confidence),
        ):
            raw = scores.get(name)
            if raw is None:
                status = CriterionStatus.FAIL if t.critical else CriterionStatus.REVIEW
                criteria.append(CriterionResult(name, None, status, t.accept, t.review, t.critical, "missing_score"))
                if t.critical:
                    has_critical_fail = True
                    reasons.append(f"{name}:missing_critical")
                else:
                    has_review = True
                    reasons.append(f"{name}:missing")
                continue

            s = float(raw)
            status = t.evaluate(s)
            criteria.append(CriterionResult(name, s, status, t.accept, t.review, t.critical))

            if status == CriterionStatus.FAIL:
                if t.critical:
                    has_critical_fail = True
                    reasons.append(f"{name}:fail({s:.3f}<{t.review})")
                else:
                    has_review = True
                    reasons.append(f"{name}:low({s:.3f})")
            elif status == CriterionStatus.REVIEW:
                has_review = True
                reasons.append(f"{name}:review({t.review}<= {s:.3f}< {t.accept})")

        if has_critical_fail:
            decision = Decision.REJECT
        elif has_review:
            decision = Decision.MANUAL_REVIEW
        else:
            decision = Decision.ACCEPT

        result = DecisionResult(
            decision=decision, reasons=reasons or ["all_criteria_passed"],
            criteria=criteria, policy_version=POLICY_VERSION,
            thresholds_snapshot=self.thresholds.to_dict(),
            scores_raw=dict(scores),
        )

        logger.info(
            "decision=%s request_id=%s policy_version=%s thresholds=%s scores=%s reasons=%s",
            decision.value, request_id, POLICY_VERSION,
            json.dumps(result.thresholds_snapshot, ensure_ascii=False),
            json.dumps(result.scores_raw, ensure_ascii=False), result.reasons,
        )
        return result
