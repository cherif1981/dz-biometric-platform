"""Fail-closed orchestration for trained biometric models.

This module deliberately does not synthesize confidence scores. Face verification
is delegated to the configured InsightFace service. Presentation-attack detection
is accepted only when a trained MiniFASNet model actually ran; heuristic fallbacks
are treated as unavailable, never as proof that a face is live.
"""

from __future__ import annotations

import math
from typing import Any


class BiometricAI:
    """Coordinate existing face and anti-spoof services with fail-closed semantics.

    Dependencies can be injected in tests. In production, existing services are
    imported lazily so importing this package does not download or load model files.
    """

    TRUSTED_SPOOF_METHODS = frozenset({"minifasnet_v2"})

    def __init__(self, face_service: Any | None = None, antispoof_service: Any | None = None):
        if face_service is None:
            from src.services.face_service import FaceService

            face_service = FaceService.get()
        if antispoof_service is None:
            from src.core.config import settings
            from src.services.antispoofing_service import AntiSpoofing

            antispoof_service = AntiSpoofing(
                getattr(settings, "ANTISPOOF_THRESHOLD", 0.45)
            )
        self.face_service = face_service
        self.antispoof_service = antispoof_service

    def verify_face(self, id_image: bytes, selfie: bytes) -> dict[str, Any]:
        """Run the existing trained face matcher and validate its output."""
        try:
            result = self.face_service.verify(id_image, selfie)
        except Exception:
            return {"available": False, "is_match": False, "similarity": None,
                    "reason": "face_model_inference_failed"}

        if not isinstance(result, dict) or result.get("error"):
            return {"available": False, "is_match": False, "similarity": None,
                    "reason": "face_model_unavailable"}

        similarity = result.get("similarity")
        if not isinstance(similarity, (int, float)) or not math.isfinite(float(similarity)):
            return {"available": False, "is_match": False, "similarity": None,
                    "reason": "invalid_face_model_output"}

        return {
            "available": True,
            "is_match": bool(result.get("is_match", False)),
            "similarity": float(similarity),
            "reason": None,
        }

    def detect_spoof(self, selfie: bytes) -> dict[str, Any]:
        """Use a trained presentation-attack model; reject heuristic-only output.

        A score is returned only when a trusted trained model produced it. Missing
        weights, model errors, or heuristic fallback all produce score=None.
        """
        try:
            result = self.antispoof_service.check(selfie)
        except Exception:
            return {"available": False, "is_real": False, "score": None,
                    "method": "unavailable", "reason": "antispoof_inference_failed"}

        if not isinstance(result, dict):
            result = {}
        method = result.get("method")
        score = result.get("score")
        if method not in self.TRUSTED_SPOOF_METHODS:
            return {"available": False, "is_real": False, "score": None,
                    "method": "unavailable", "reason": "trained_antispoof_model_unavailable"}
        if not isinstance(score, (int, float)) or not math.isfinite(float(score)) or not 0 <= float(score) <= 1:
            return {"available": False, "is_real": False, "score": None,
                    "method": "unavailable", "reason": "invalid_antispoof_model_output"}

        return {"available": True, "is_real": bool(result.get("is_real", False)),
                "score": float(score), "method": method, "reason": None}

    def assess(self, id_image: bytes, selfie: bytes) -> dict[str, Any]:
        """Run both checks and provide explicit availability flags."""
        face = self.verify_face(id_image, selfie)
        spoof = self.detect_spoof(selfie)
        accepted = (
            face["available"] and face["is_match"]
            and spoof["available"] and spoof["is_real"]
        )
        return {"accepted": accepted, "face": face, "spoof": spoof}
