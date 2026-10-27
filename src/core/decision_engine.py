"""واجهة توافق: تفوّض القرار إلى UnifiedDecisionEngine (مصدر الحقيقة الوحيد)."""
from __future__ import annotations

from typing import Optional

from .decision_policy import (
    UnifiedDecisionEngine, DecisionThresholds, DecisionResult,
    Decision, CriterionStatus,
)

__all__ = ["DecisionEngine", "DecisionResult", "Decision", "CriterionStatus"]


class DecisionEngine:
    """محرك قرار متوافق مع الواجهة القديمة.

    - يقبل `thresholds: dict` (كما كان سابقاً) ويحوّلها إلى DecisionThresholds.
    - يقبل `scores: dict` ويرجع DecisionResult.
    - يحفظ `last_result` للتوافق مع مستدعين قد يقرؤونه.
    """

    def __init__(self, thresholds: Optional[dict] = None, strict_critical: bool = True):
        t = DecisionThresholds.from_settings(None)
        if thresholds:
            # دعم المفاتيح القديمة: face/liveness/antispoof/ocr
            alias = {"face": "face_similarity", "ocr": "ocr_confidence"}
            fields = {}
            for k, v in thresholds.items():
                name = alias.get(k, k)
                base = getattr(t, name)
                # نستخدم النمط النسبي كما في السلوك القديم (threshold * 0.9)
                fields[name] = type(base)(
                    name=base.name, accept=float(v),
                    review_factor=getattr(base, "review_factor", 0.9),
                    critical=base.critical,
                )
            t = DecisionThresholds(**{**{k: getattr(t, k) for k in
                                         ("face_similarity","liveness","antispoof","ocr_confidence")},
                                      **fields})
        self.thresholds = t
        self._engine = UnifiedDecisionEngine(t, strict_critical=strict_critical)
        self.last_result: Optional[DecisionResult] = None

    def decide(self, scores: dict) -> DecisionResult:
        self.last_result = self._engine.decide(scores)
        return self.last_result

    # واجهة مساعدة للتوافق مع الكود القديم الذي قد يقرأ الثقة/النقاط
    def score(self, scores: dict) -> float:
        """يبقى متاحاً للتوافق فقط، ولا يُستخدم في القرار."""
        vals = [float(v) for v in scores.values() if v is not None]
        return sum(vals) / len(vals) if vals else 0.0
