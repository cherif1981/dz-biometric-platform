
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Dict

from src.core.decision_engine import DecisionEngine, DecisionResult


class ReportBuilder:
    """يبني تقريرًا يعتمد حصريًا على مخرجات DecisionEngine.

    لا يحتوي على أي قيمة قرار مكتوبة يدويًا (لا VERIFIED، لا REJECTED).
    """

    def __init__(self, decision_engine: DecisionEngine):
        self.engine = decision_engine

    def build(self, subject_id: str, scores: Dict[str, float]) -> Dict[str, Any]:
        decision: DecisionResult = self.engine.decide(scores)

        return {
            "subject_id": subject_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "decision": {
                "final_status": decision.final_status,        # ← من DecisionEngine
                "confidence": decision.confidence,
                "reasons": decision.reasons,
            },
            "scores": decision.per_modality_scores,
            "applied_thresholds": decision.applied_thresholds,
            "engine_version": "1.0.0",
        }
