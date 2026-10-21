"""Face service + adapter for VerificationEngine."""
from typing import Dict, Optional
from loguru import logger

from src.services.base_service import BaseVerificationService


class FaceVerificationService(BaseVerificationService):
    """Scoring service (الواجهة القديمة)."""
    modality = "face_similarity"

    def verify(self, payload: Dict) -> Dict[str, float]:
        score = payload.get("face_score", 0.0)
        return {self.modality: float(score)}


class FaceService:
    """Adapter for VerificationEngine.

    API:
        FaceService.get() -> singleton
        instance.verify(id_bytes, selfie_bytes) -> {"similarity": float, ...}
    """
    _instance: Optional["FaceService"] = None

    def __init__(self):
        self._detector = None
        self._embedder = None
        self._matcher = None

    def _ensure_backend(self):
        if self._detector is not None:
            return
        from src.modules.face_verification.detector import FaceDetector
        from src.modules.face_verification.embeddings import EmbeddingExtractor
        from src.modules.face_verification.matcher import FaceMatcher
        self._detector = FaceDetector()
        self._embedder = EmbeddingExtractor()
        self._matcher = FaceMatcher()

    @classmethod
    def get(cls) -> "FaceService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def verify(self, id_bytes: bytes, selfie_bytes: bytes) -> Dict:
        self._ensure_backend()
        try:
            d_id = self._detector.detect(id_bytes)
            d_selfie = self._detector.detect(selfie_bytes)
            e_id = self._embedder.extract(d_id)
            e_selfie = self._embedder.extract(d_selfie)
            r = self._matcher.compare(e_id, e_selfie)
            if isinstance(r, dict):
                sim = float(r.get("similarity", r.get("score", 0.0)))
                return {"similarity": sim, **r}
            return {"similarity": float(r)}
        except Exception as e:
            logger.error(f"FaceService.verify failed: {e}")
            raise


# backward-compat helpers (كانت مُعلّقة على دوالّ غير موجودة)
def compare(emb1, emb2):
    from src.modules.face_verification.matcher import FaceMatcher
    return FaceMatcher().compare(emb1, emb2)


def detect(image_bytes):
    from src.modules.face_verification.detector import FaceDetector
    return FaceDetector().detect(image_bytes)


def extract_embedding(image_bytes):
    from src.modules.face_verification.detector import FaceDetector
    from src.modules.face_verification.embeddings import EmbeddingExtractor
    return EmbeddingExtractor().extract(FaceDetector().detect(image_bytes))
