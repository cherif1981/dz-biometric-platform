
from typing import Dict
from src.services.base_service import BaseVerificationService

class AntispoofingService(BaseVerificationService):

    def __init__(self, threshold=None, *args, **kwargs):
        """Backward-compat: accept an optional threshold."""
        self.threshold = threshold
    modality = "antispoofing"

    def verify(self, payload: Dict) -> Dict[str, float]:
        score = payload.get("antispoofing_score", 0.0)
        return {self.modality: float(score)}

# Backward-compat alias

# Backward-compat alias (used by verification_service.py)
AntiSpoofing = AntispoofingService
