"""Face verification via insightface (buffalo_l)."""
from __future__ import annotations
import logging
from typing import Optional
import numpy as np
import cv2

logger = logging.getLogger(__name__)


class FaceVerificationService:
    """1:1 face verification: insightface embeddings + cosine similarity."""

    _instance: Optional["FaceVerificationService"] = None

    def __init__(self, model_name: str = "buffalo_l", det_thresh: float = 0.5):
        from insightface.app import FaceAnalysis
        self.modality = "face_similarity"
        self.det_thresh = det_thresh
        self._app = FaceAnalysis(name=model_name, providers=["CPUExecutionProvider"])
        self._app.prepare(ctx_id=0, det_size=(640, 640), det_thresh=det_thresh)
        logger.info(f"FaceVerificationService ready | model={model_name} | det_thresh={det_thresh}")

    @classmethod
    def get(cls) -> "FaceVerificationService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _embed(self, img: np.ndarray) -> Optional[np.ndarray]:
        """Extract normalized embedding; pads tightly-cropped faces (LFW-style)."""
        faces = self._app.get(img)
        if not faces:
            for pad in (60, 80):
                padded = cv2.copyMakeBorder(img, pad, pad, pad, pad, cv2.BORDER_REFLECT)
                cand = [f for f in self._app.get(padded) if f.det_score >= self.det_thresh]
                if cand:
                    faces = cand
                    break
        if not faces:
            return None
        faces = sorted(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]),
                       reverse=True)
        return faces[0].normed_embedding

    @staticmethod
    def _decode(b: bytes) -> Optional[np.ndarray]:
        arr = np.frombuffer(b, np.uint8)
        return cv2.imdecode(arr, cv2.IMREAD_COLOR)

    def verify(self, id_bytes: bytes, selfie_bytes: bytes) -> dict:
        """Returns {face_similarity: float in [0,1]} (cosine remapped from [-1,1])."""
        id_img = self._decode(id_bytes)
        selfie_img = self._decode(selfie_bytes)
        if id_img is None or selfie_img is None:
            return {self.modality: 0.0, "face_similarity": 0.0}

        e1 = self._embed(id_img)
        e2 = self._embed(selfie_img)
        if e1 is None or e2 is None:
            # فشل كشف — ليس تشابهاً منخفضاً
            return {
                "face_similarity": None,
                "similarity": None,
                "score": None,
                "face_score": None,
                "detection_failed": True,
            }

        cos = float(np.dot(e1, e2))                         # in [-1, 1]
        score = float(np.clip((cos + 1.0) / 2.0, 0.0, 1.0)) # → [0, 1]
        # ارجع كل المفاتيح المحتملة لضمان التوافق مع أي مستدعٍ
        return {
            "face_similarity": score,
            "similarity": score,
            "score": score,
            "face_score": score,
        }
