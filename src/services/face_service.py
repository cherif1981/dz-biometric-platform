
from typing import Dict
from src.services.base_service import BaseVerificationService


class FaceVerificationService(BaseVerificationService):
    modality = "face_similarity"

    def verify(self, payload: Dict) -> Dict[str, float]:
        # ⚠️ هنا مكان منطق مطابقة الوجه (embedding similarity).
        # المهم: تُرجع درجة فقط، لا تقارنها بأي عتبة.
        score = payload.get("face_score", 0.0)
        return {self.modality: float(score)}
