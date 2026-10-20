
from typing import Dict
from src.services.base_service import BaseVerificationService


class AntispoofingService(BaseVerificationService):
    modality = "antispoofing"

    def verify(self, payload: Dict) -> Dict[str, float]:
        score = payload.get("antispoofing_score", 0.0)
        return {self.modality: float(score)}
