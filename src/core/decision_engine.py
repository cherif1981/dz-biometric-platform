import json
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class DecisionResult:
    final_status: str
    confidence: float
    per_modality_scores: Dict[str, float]
    applied_thresholds: Dict[str, float]
    reasons: List[str] = field(default_factory=list)


class DecisionEngine:
    """المصدر الوحيد لاتخاذ القرار في النظام."""

    def __init__(self, thresholds_path: str = "config/thresholds.yaml"):
        with open(thresholds_path, encoding="utf-8") as f:
            if thresholds_path.endswith(".json"):
                self.thresholds = json.load(f)
            else:
                import yaml

                self.thresholds = yaml.safe_load(f)

    def decide(self, scores: Dict[str, float]) -> DecisionResult:
        reasons, passed = [], []
        for modality, score in scores.items():
            thr = self.thresholds.get(modality)
            if thr is None:
                raise ValueError(f"No threshold configured for modality: {modality}")
            if score >= thr:
                passed.append(modality)
            else:
                reasons.append(f"{modality}: {score:.3f} < {thr}")

        if len(passed) == len(scores) and scores:
            status = "VERIFIED"
        elif any(scores[m] >= self.thresholds[m] * 0.9 for m in scores if m not in passed):
            status = "REVIEW"
        else:
            status = "REJECTED"

        confidence = sum(scores.values()) / len(scores) if scores else 0.0
        return DecisionResult(
            final_status=status,
            confidence=round(confidence, 4),
            per_modality_scores=scores,
            applied_thresholds=self.thresholds,
            reasons=reasons,
        )
