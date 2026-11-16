"""AI decision engine — backward compatible, auto-loads YAML thresholds."""
from __future__ import annotations

from pathlib import Path

from ...core.decision_policy import (
    CriterionStatus,
    CriterionThreshold,
    Decision,
    DecisionResult,
    DecisionThresholds,
    UnifiedDecisionEngine,
)

__all__ = ["AIDecisionEngine", "CriterionStatus", "Decision", "DecisionEngine", "DecisionResult"]


def _load_yaml_thresholds(path: str) -> dict | None:
    """يقرأ config/thresholds.yaml ويُرجع dict مسطّحاً."""
    p = Path(path)
    if not p.exists():
        return None
    try:
        import yaml
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception:
        return None
    flat = {}
    for k, v in data.items():
        if isinstance(v, dict):
            for sub in ("accept", "threshold", "min", "value"):
                if sub in v and isinstance(v[sub], (int, float)):
                    flat[k] = float(v[sub])
                    break
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            flat[k] = float(v)
    return flat


class AIDecisionEngine:
    """Backward-compatible wrapper. Default: loads config/thresholds.yaml."""

    def __init__(
        self,
        min_face_similarity: float | None = None,
        min_liveness: float | None = None,
        min_antispoof: float | None = None,
        min_ocr_confidence: float | None = None,
        review_max_risk: float | None = None,
        max_tampering: float | None = None,
        thresholds_path: str | None = "config/thresholds.yaml",
        **extra,
    ):
        base = DecisionThresholds.from_settings(None)

        # 1) حمّل YAML افتراضياً (يمكن تعطيله بـ thresholds_path=None)
        yaml_data = _load_yaml_thresholds(thresholds_path) if thresholds_path else None

        # 2) طبّق قيم YAML على العتبات (إن وُجدت)
        if yaml_data:
            def _from_yaml(name, yaml_key, fallback):
                val = yaml_data.get(yaml_key)
                if val is None:
                    return fallback
                try:
                    return CriterionThreshold(
                        name=name, accept=float(val),
                        review_factor=getattr(fallback, "review_factor", 0.9),
                        critical=fallback.critical,
                    )
                except (TypeError, ValueError):
                    return fallback

            base = DecisionThresholds(
                face_similarity=_from_yaml("face_similarity", "face_similarity", base.face_similarity),
                liveness=_from_yaml("liveness", "liveness", base.liveness),
                antispoof=_from_yaml("antispoof", "antispoofing",
                                     _from_yaml("antispoof", "antispoofing_accept", base.antispoof)),
                ocr_confidence=_from_yaml("ocr_confidence", "ocr_confidence", base.ocr_confidence),
            )

        # 3) legacy: review_max_risk / max_tampering
        if review_max_risk is not None and min_face_similarity is None:
            min_face_similarity = round(1.0 - review_max_risk, 6)
        if max_tampering is not None and min_antispoof is None:
            min_antispoof = round(1.0 - max_tampering, 6)

        # 4) explicit override يفوز دائماً
        def _build(name, accept, fallback):
            if accept is None:
                return fallback
            try:
                return CriterionThreshold(
                    name=name, accept=float(accept),
                    review_factor=getattr(fallback, "review_factor", 0.9),
                    critical=fallback.critical,
                )
            except (TypeError, ValueError):
                return fallback

        self.thresholds = DecisionThresholds(
            face_similarity=_build("face_similarity", min_face_similarity, base.face_similarity),
            liveness=_build("liveness", min_liveness, base.liveness),
            antispoof=_build("antispoof", min_antispoof, base.antispoof),
            ocr_confidence=_build("ocr_confidence", min_ocr_confidence, base.ocr_confidence),
        )
        self._engine = UnifiedDecisionEngine(self.thresholds)
        self.last_result: DecisionResult | None = None

    @property
    def min_face_similarity(self) -> float:
        return self.thresholds.face_similarity.accept

    @property
    def min_liveness(self) -> float:
        return self.thresholds.liveness.accept

    @property
    def min_antispoof(self) -> float:
        return self.thresholds.antispoof.accept

    @property
    def min_ocr_confidence(self) -> float:
        return self.thresholds.ocr_confidence.accept

    def decide(self, scores: dict) -> DecisionResult:
        self.last_result = self._engine.decide(scores)
        return self.last_result


DecisionEngine = AIDecisionEngine
