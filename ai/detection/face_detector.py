import numpy as np
from typing import List, Dict
from ai.configs.settings import settings
from insightface.app import FaceAnalysis


class FaceDetector:
    """كاشف وجوه يستخدم InsightFace بدلاً من dlib/face_recognition."""

    def __init__(self):
        self.app = FaceAnalysis(
            name="buffalo_l",
            providers=["CUDAExecutionProvider", "CPUExecutionProvider"]
        )
        self.app.prepare(ctx_id=0, det_size=(640, 640))

    def _detect_raw(self, image):
        return self.app.get(image)

    def detect(self, image) -> Dict:
        faces = self._detect_raw(image)
        locations = []
        for f in faces:
            x1, y1, x2, y2 = f.bbox.astype(int).tolist()
            locations.append([y1, x2, y2, x1])
        return {
            "count": len(locations),
            "locations": locations,
        }

    def crop_faces(self, image) -> List:
        faces = self._detect_raw(image)
        crops = []
        for f in faces:
            x1, y1, x2, y2 = f.bbox.astype(int).tolist()
            h, w = y2 - y1, x2 - x1
            pad_h, pad_w = int(h * 0.2), int(w * 0.2)
            top = max(0, y1 - pad_h)
            bottom = min(image.shape[0], y2 + pad_h)
            left = max(0, x1 - pad_w)
            right = min(image.shape[1], x2 + pad_w)
            crops.append(image[top:bottom, left:right])
        return crops

    def embeddings(self, image) -> List:
        return [f.embedding for f in self._detect_raw(image)]
