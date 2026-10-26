"""
Passive liveness detector.

Delegates to a trained ONNX anti-spoofing model (MiniFASNetV2).
Previously this module used a heuristic (Laplacian + saturation + FFT),
which is NOT a liveness detector and can be defeated by printed photos,
screen replays, and video replays.

Design:
- Interface preserved: predict(image_bytes) -> {is_live, score, threshold}
- Fail-closed: ANY error (missing model, decode failure, no face, inference error)
  returns is_live=False. Absence of a result is NOT success.
- Threshold comes from config/thresholds.yaml (single source of truth).
"""

import os
from pathlib import Path
from typing import Dict, Optional

from src.core.thresholds import get_thresholds
from src.modules.liveness.anti_spoofing import AntiSpoofing

_MODEL_ENV = "ANTISPOOF_MODEL_PATH"
_DEFAULT_MODEL = Path("models/MiniFASNetV2.onnx")

_detector: Optional[AntiSpoofing] = None


def _model_path() -> Path:
    return Path(os.getenv(_MODEL_ENV, str(_DEFAULT_MODEL)))


def _get_detector() -> AntiSpoofing:
    """Lazy-load the ONNX detector once. Raises if model file is missing."""
    global _detector
    if _detector is None:
        path = _model_path()
        if not path.exists():
            raise FileNotFoundError(
                f"Anti-spoofing model not found at {path}. "
                "Ship the model file or set ANTISPOOF_MODEL_PATH. "
                "Refusing to fall back to heuristic — absence of model is NOT success."
            )
        threshold = get_thresholds().antispoofing
        _detector = AntiSpoofing(model_path=str(path), threshold=threshold)
    return _detector


class PassiveLiveness:
    """
    Real liveness detector (ONNX MiniFASNetV2).
    Replaces the previous heuristic. Fail-closed on every error path.
    """

    def predict(self, image_bytes: bytes) -> Dict:
        # Fail-closed: capture ALL failures as is_live=False.
        try:
            detector = _get_detector()
            result = detector.check(image_bytes)
        except Exception as e:
            return {
                "is_live": False,
                "score": 0.0,
                "threshold": get_thresholds().antispoofing,
                "error": f"{type(e).__name__}: {e}",
            }

        # AntiSpoofing.check already returns spoof=True on internal errors,
        # but we also surface the error text for observability.
        if result.get("error"):
            return {
                "is_live": False,
                "score": float(result.get("score", 0.0)),
                "threshold": get_thresholds().antispoofing,
                "error": result["error"],
            }

        return {
            "is_live": not bool(result["spoof"]),
            "score": float(result["score"]),
            "threshold": get_thresholds().antispoofing,
            "error": None,
        }
