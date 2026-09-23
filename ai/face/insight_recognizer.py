import cv2
import numpy as np
from typing import Dict, Optional, Tuple
from ai.configs.settings import settings

try:
    from insightface.app import FaceAnalysis
    INSIGHTFACE_AVAILABLE = True
except ImportError:
    INSIGHTFACE_AVAILABLE = False


class InsightFaceRecognizer:
    def __init__(self, model_name: str = "buffalo_l"):
        if not INSIGHTFACE_AVAILABLE:
            raise ImportError("insightface غير مثبت. نفّذ: pip install insightface onnxruntime")

        self.app = FaceAnalysis(
            name=model_name,
            providers=["CPUExecutionProvider"],  # غيّر إلى CUDAExecutionProvider مع GPU
        )
        self.app.prepare(ctx_id=0, det_size=(640, 640))
        self.threshold = getattr(settings, "FACE_THRESHOLD", 0.45)  # ArcFace عادة أقل من dlib

    def _get_best_face(self, image: np.ndarray):
        faces = self.app.get(image)
        if not faces:
            return None
        # أكبر وجه
        faces = sorted(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]), reverse=True)
        return faces[0]

    def encode(self, image: np.ndarray) -> Optional[Tuple[np.ndarray, float]]:
        face = self._get_best_face(image)
        if face is None:
            return None

        embedding = face.normed_embedding  # بالفعل مُطَبَّع
        # جودة تقريبية من det_score
        quality = float(face.det_score)
        return embedding, quality

    def verify(self, img1: np.ndarray, img2: np.ndarray) -> Dict:
        res1 = self.encode(img1)
        res2 = self.encode(img2)

        if res1 is None or res2 is None:
            return {
                "success": False,
                "verified": False,
                "similarity": 0.0,
                "distance": 1.0,
                "message": "لم يتم العثور على وجه واضح في إحدى الصورتين",
            }

        emb1, q1 = res1
        emb2, q2 = res2

        # Cosine similarity (لأن embeddings مُطَبَّعة)
        similarity = float(np.dot(emb1, emb2))
        distance = 1.0 - similarity
        verified = similarity >= self.threshold

        return {
            "success": True,
            "verified": verified,
            "similarity": round(similarity, 4),
            "distance": round(distance, 4),
            "confidence": round(similarity * min(q1, q2), 4),
            "quality_card": round(q1, 3),
            "quality_selfie": round(q2, 3),
            "message": "✅ تطابق" if verified else "❌ لا يوجد تطابق",
            "model": "insightface-buffalo_l",
        }