"""واجهة توافق: تفوّض القرار إلى UnifiedDecisionEngine.

يقبل:
- dict: {name: threshold} أو {name: {'accept': ...}}
- str/Path: مسار ملف YAML
- None: عتبات افتراضية
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from .decision_policy import (
    UnifiedDecisionEngine, DecisionThresholds, DecisionResult,
    Decision, CriterionStatus,
)

__all__ = ["DecisionEngine", "DecisionResult", "Decision", "CriterionStatus"]


class DecisionEngine:
    def __init__(self, thresholds: Union[dict, str, Path, None] = None,
                 strict_critical: bool = True):
        t = DecisionThresholds.from_settings(None)

        if thresholds is not None:
            # مسار YAML → حمّله وأسطحه
            if isinstance(thresholds, (str, Path)):
                path = Path(thresholds)
                if path.exists():
                    try:
                        import yaml
                        with open(path, encoding="utf-8") as f:
                            data = yaml.safe_load(f) or {}
                        thresholds = self._flatten_yaml(data)
                    except Exception:
                        thresholds = None
                else:
                    thresholds = None

            # dict → استخدمه
            if isinstance(thresholds, dict) and thresholds:
                alias = {"face": "face_similarity", "ocr": "ocr_confidence"}
                fields = {}
                for k, v in thresholds.items():
                    name = alias.get(k, k)
                    base = getattr(t, name, None)
                    if base is None:
                        continue
                    try:
                        fields[name] = type(base)(
                            name=base.name, accept=float(v),
                            review_factor=getattr(base, "review_factor", 0.9),
                            critical=base.critical,
                        )
                    except (TypeError, ValueError):
                        continue
                valid = ("face_similarity", "liveness", "antispoof", "ocr_confidence")
                t = DecisionThresholds(
                    **{**{k: getattr(t, k) for k in valid}, **fields}
                )

        self.thresholds = t
        self._engine = UnifiedDecisionEngine(t, strict_critical=strict_critical)
        self.last_result: Optional[DecisionResult] = None

    @staticmethod
    def _flatten_yaml(data: dict) -> dict:
        flat = {}
        for k, v in (data or {}).items():
            if isinstance(v, dict):
                for sub_k in ("accept", "threshold", "min", "value"):
                    if sub_k in v and isinstance(v[sub_k], (int, float)):
                        flat[k] = float(v[sub_k])
                        break
            elif isinstance(v, (int, float)):
                flat[k] = float(v)
        return flat

    def decide(self, scores: dict) -> DecisionResult:
        self.last_result = self._engine.decide(scores)
        return self.last_result

    def score(self, scores: dict) -> float:
        vals = [float(v) for v in scores.values() if v is not None]
        return sum(vals) / len(vals) if vals else 0.0
