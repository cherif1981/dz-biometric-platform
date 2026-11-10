"""Face matching service — Path A of KYC verification.

Independent from document authenticity (Path B). Produces a similarity
score and a match decision ONLY. No document logic here.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import numpy as np

_DEFAULT_THRESHOLD = float(os.getenv("FACE_MATCH_THRESHOLD", "0.35"))
_MODEL_NAME = os.getenv("FACE_MATCH_MODEL", "buffalo_l")
_DET_SIZE = (640, 640)


class FaceMatchService:
    """Lazy-loaded face embedding extractor + matcher.

    Embeddings are L2-normalized 512-d vectors; similarity is cosine.
    """

    def __init__(self, model_name: str = _MODEL_NAME, threshold: float = _DEFAULT_THRESHOLD):
        self._model_name = model_name
        self.threshold = threshold
        self._app = None  # lazy

    # ── internal ──────────────────────────────────────────────────────
    def _ensure_loaded(self):
        if self._app is not None:
            return
        from insightface.app import FaceAnalysis
        app = FaceAnalysis(name=self._model_name, providers=["CPUExecutionProvider"])
        app.prepare(ctx_id=-1, det_size=_DET_SIZE)
        self._app = app

    def _extract(self, image_bgr: np.ndarray) -> np.ndarray:
        if image_bgr is None or image_bgr.size == 0:
            raise ValueError("empty image")
        self._ensure_loaded()
        faces = self._app.get(image_bgr)
        if len(faces) == 0:
            raise ValueError("no face detected")
        if len(faces) > 1:
            raise ValueError(f"multiple faces detected ({len(faces)}); expected 1")
        return faces[0].normed_embedding.astype(np.float32)

    # ── public ────────────────────────────────────────────────────────
    def similarity(self, selfie_bgr: np.ndarray, document_face_bgr: np.ndarray) -> float:
        e1 = self._extract(selfie_bgr)
        e2 = self._extract(document_face_bgr)
        return float(np.clip(np.dot(e1, e2), -1.0, 1.0))

    def match(self, selfie_bgr: np.ndarray, document_face_bgr: np.ndarray,
              threshold: Optional[float] = None) -> dict:
        t = self.threshold if threshold is None else threshold
        sim = self.similarity(selfie_bgr, document_face_bgr)
        return {
            "similarity": sim,
            "match": sim >= t,
            "threshold": t,
        }


_service: Optional[FaceMatchService] = None

def get_face_match_service() -> FaceMatchService:
    """Process-wide singleton."""
    global _service
    if _service is None:
        _service = FaceMatchService()
    return _service
