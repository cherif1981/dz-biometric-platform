import face_recognition
import numpy as np
import cv2
from typing import Dict, Optional, Tuple
from ai.configs.settings import settings

# محاولة استخدام MediaPipe للمحاذاة
try:
    from ai.face.mediapipe_alignment import align_face, get_aligner
    HAS_MEDIAPIPE = True
except ImportError:
    HAS_MEDIAPIPE = False


class FaceRecognizer:
    def __init__(self):
        self.threshold = settings.FACE_THRESHOLD
        self.num_jitters = getattr(settings, "FACE_NUM_JITTERS", 2)
        self.encoding_model = getattr(settings, "FACE_ENCODING_MODEL", "large")
        self.detection_model = getattr(settings, "FACE_MODEL", "hog")

    def _to_rgb(self, image: np.ndarray) -> np.ndarray:
        if image.ndim == 2:
            return cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        if image.shape[2] == 4:
            return cv2.cvtColor(image, cv2.COLOR_BGRA2RGB)
        return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    def encode(self, image: np.ndarray) -> Optional[Tuple[np.ndarray, float]]:
        """
        Returns (embedding, quality_score) or None.
        Uses MediaPipe alignment when available.
        """
        quality = 0.5

        # ===== 1. محاولة المحاذاة بـ MediaPipe =====
        if HAS_MEDIAPIPE:
            aligned = align_face(image, output_size=(160, 160))
            if aligned is not None:
                rgb = aligned
                quality = get_aligner().face_quality_score(image)
                quality = max(quality, 0.6)  # المحاذاة الناجحة تعني جودة أفضل
            else:
                rgb = self._to_rgb(image)
        else:
            rgb = self._to_rgb(image)

        # ===== 2. استخراج الـ Embedding =====
        locations = face_recognition.face_locations(
            rgb, model=self.detection_model
        )
        if not locations:
            return None

        # أكبر وجه
        locations = sorted(
            locations,
            key=lambda loc: (loc[2] - loc[0]) * (loc[1] - loc[3]),
            reverse=True,
        )

        encodings = face_recognition.face_encodings(
            rgb,
            known_face_locations=[locations[0]],
            num_jitters=self.num_jitters,
            model=self.encoding_model,
        )
        if not encodings:
            return None

        return encodings[0], round(quality, 3)

    def verify(self, img1: np.ndarray, img2: np.ndarray) -> Dict:
        res1 = self.encode(img1)
        res2 = self.encode(img2)

        if res1 is None or res2 is None:
            return {
                "success": False,
                "verified": False,
                "similarity": 0.0,
                "distance": 1.0,
                "quality_card": 0.0 if res1 is None else res1[1],
                "quality_selfie": 0.0 if res2 is None else res2[1],
                "message": "لم يتم العثور على وجه واضح في إحدى الصورتين",
                "alignment": "mediapipe" if HAS_MEDIAPIPE else "none",
            }

        enc1, q1 = res1
        enc2, q2 = res2

        distance = float(face_recognition.face_distance([enc1], enc2)[0])
        similarity = max(0.0, 1.0 - distance)
        verified = distance < self.threshold
        confidence = similarity * min(q1, q2)

        return {
            "success": True,
            "verified": verified,
            "similarity": round(similarity, 4),
            "distance": round(distance, 4),
            "confidence": round(confidence, 4),
            "quality_card": q1,
            "quality_selfie": q2,
            "message": "✅ تطابق" if verified else "❌ لا يوجد تطابق",
            "alignment": "mediapipe" if HAS_MEDIAPIPE else "none",
        }