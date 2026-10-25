"""
Liveness service — thin wrapper around the passive liveness detector.

- Accepts an optional `threshold` (falls back to config/thresholds.yaml).
- Fail-closed: any error -> is_live=False.
"""
from typing import Optional, Dict, Any

from src.modules.liveness.passive import PassiveLiveness
from src.core.thresholds import get_thresholds


class LivenessService:
    def __init__(self, threshold: Optional[float] = None, *args, **kwargs):
        self.threshold = threshold if threshold is not None else get_thresholds().liveness
        self._detector = PassiveLiveness()

    def check(self, image_bytes: bytes) -> Dict[str, Any]:
        try:
            result = self._detector.predict(image_bytes)
            return {
                "is_live": bool(result.get("is_live", False)),
                "score": float(result.get("score", 0.0)),
                "threshold": self.threshold,
                "error": result.get("error"),
            }
        except Exception as e:
            # Fail-closed
            return {
                "is_live": False,
                "score": 0.0,
                "threshold": self.threshold,
                "error": f"{type(e).__name__}: {e}",
            }
