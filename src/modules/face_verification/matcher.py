import numpy as np
from src.core.config import settings


class FaceMatcher:
    def __init__(self, threshold: float | None = None):
        self.threshold = threshold if threshold is not None else settings.FACE_MATCH_THRESHOLD

    def compare(self, emb1: np.ndarray | None, emb2: np.ndarray | None) -> dict:
        if emb1 is None or emb2 is None:
            return {"match": False, "similarity": 0.0, "reason": "face_not_detected"}

        a = emb1 / (np.linalg.norm(emb1) + 1e-9)
        b = emb2 / (np.linalg.norm(emb2) + 1e-9)
        cos = float(np.dot(a, b))
        return {
            "match": cos >= self.threshold,
            "similarity": cos,
            "threshold": self.threshold,
        }