"""
Liveness service — delegates to AntiSpoofing (MiniFASNet ensemble).
Keeps the check(image_bytes) interface backward-compatible with verification_service.
"""
import cv2
import numpy as np

from src.services.antispoofing_service import AntiSpoofing


class LivenessService:
    def __init__(self, threshold: float = 0.45):
        self.threshold = threshold
        self._detector = AntiSpoofing(threshold=threshold)

    def _decode(self, b):
        return cv2.imdecode(np.frombuffer(b, np.uint8), cv2.IMREAD_COLOR)

    def check(self, image_bytes):
        img = self._decode(image_bytes)
        if img is None:
            return {"score": 0.0, "is_live": False, "method": "none",
                    "reason": "decode_failed", "threshold": self.threshold}

        result = self._detector.check(image_bytes)
        return {
            "score": result.get("score", 0.0),
            "is_live": bool(result.get("is_real", False)),
            "method": result.get("method", "unknown"),
            "threshold": self.threshold,
        }
