import face_recognition
import numpy as np
import cv2
from typing import Dict, Optional, Tuple
from ai.configs.settings import settings


class FaceRecognizer:
    def __init__(self):
        self.threshold = settings.FACE_THRESHOLD
        self.num_jitters = settings.FACE_NUM_JITTERS
        self.encoding_model = getattr(settings, "FACE_ENCODING_MODEL", "large")
        self.detection_model = getattr(settings, "FACE_MODEL", "hog")
        self.min_face_size = getattr(settings, "FACE_MIN_SIZE", 80)

    def _to_rgb(self, image: np.ndarray) -> np.ndarray:
        if image.ndim == 2:
            return cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        if image.shape[2] == 4:
            return cv2.cvtColor(image, cv2.COLOR_BGRA2RGB)
        return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    def _face_quality(self, image: np.ndarray, location: Tuple[int, int, int, int]) -> float:
        """تقييم جودة الوجه (حجم + وضوح)."""
        top, right, bottom, left = location
        h, w = bottom - top, right - left
        if h < self.min_face_size or w < self.min_face_size:
            return 0.0

        face = image[top:bottom, left:right]
        if face.size == 0:
            return 0.0

        gray = cv2.cvtColor(face, cv2.COLOR_RGB2GRAY) if face.ndim == 3 else face
        # وضوح (Laplacian variance)
        sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
        size_score = min(1.0, (h * w) / (150 * 150))
        sharp_score = min(1.0, sharpness / 300.0)
        return round(0.6 * size_score + 0.4 * sharp_score, 3)

    def encode(self, image: np.ndarray) -> Optional[Tuple[np.ndarray, float]]:
        """يرجع (embedding, quality_score) أو None."""
        rgb = self._to_rgb(image)

        locations = face_recognition.face_locations(
            rgb,
            model=self.detection_model,
            number_of_times_to_upsample=getattr(settings, "FACE_UPSAMPLE", 1),
        )
        if not locations:
            return None

        # اختيار أكبر وجه (الأكثر احتمالاً أنه الوجه الرئيسي)
        locations = sorted(locations, key=lambda loc: (loc[2] - loc[0]) * (loc[1] - loc[3]), reverse=True)
        best_loc = locations[0]

        quality = self._face_quality(rgb, best_loc)
        if quality < 0.25:
            return None  # وجه رديء الجودة

        encodings = face_recognition.face_encodings(
            rgb,
            known_face_locations=[best_loc],
            num_jitters=self.num_jitters,
            model=self.encoding_model,
        )
        if not encodings:
            return None

        return encodings[0], quality

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
            }

        enc1, q1 = res1
        enc2, q2 = res2

        distance = float(face_recognition.face_distance([enc1], enc2)[0])
        similarity = max(0.0, 1.0 - distance)
        verified = distance < self.threshold

        # تقليل الثقة إذا كانت جودة إحدى الصورتين منخفضة
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
        }