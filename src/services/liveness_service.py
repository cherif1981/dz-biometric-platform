
from typing import Dict
from src.services.base_service import BaseVerificationService


class LivenessService(BaseVerificationService):
    modality = "liveness"

    def verify(self, payload: Dict) -> Dict[str, float]:
        score = payload.get("liveness_score", 0.0)
        return {self.modality: float(score)}
