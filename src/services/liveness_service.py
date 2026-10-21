"""Liveness service + adapter."""
from typing import Dict
from loguru import logger

from src.services.base_service import BaseVerificationService


class LivenessService(BaseVerificationService):
    modality = "liveness"

    def verify(self, payload: Dict) -> Dict[str, float]:
        score = payload.get("liveness_score", 0.0)
        return {self.modality: float(score)}

    # Adapter for VerificationEngine
    def check(self, image_bytes: bytes) -> Dict:
        try:
            from src.modules.liveness.passive import PassiveLiveness
            r = PassiveLiveness().predict(image_bytes)
            if isinstance(r, dict):
                score = float(r.get("score", r.get("real_prob", r.get("confidence", 0.0))))
                return {"score": score, **r}
            return {"score": float(r)}
        except Exception as e:
            logger.error(f"LivenessService.check failed: {e}")
            raise
