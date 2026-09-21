import face_recognition
import numpy as np
from typing import Dict, Optional
from ai.configs.settings import settings

class FaceRecognizer:
    def encode(self, image: np.ndarray) -> Optional[np.ndarray]:
        rgb = image[:, :, ::-1]
        encodings = face_recognition.face_encodings(
            rgb, num_jitters=settings.FACE_NUM_JITTERS
        )
        return encodings[0] if encodings else None

    def verify(self, img1: np.ndarray, img2: np.ndarray) -> Dict:
        enc1 = self.encode(img1)
        enc2 = self.encode(img2)
        if enc1 is None or enc2 is None:
            return {
                "success": False, "verified": False,
                "similarity": 0.0, "distance": 1.0,
                "message": "لم يتم العثور على وجه في إحدى الصورتين",
            }
        distance = float(face_recognition.face_distance([enc1], enc2)[0])
        similarity = max(0.0, 1.0 - distance)
        verified = distance < settings.FACE_THRESHOLD
        return {
            "success": True,
            "verified": verified,
            "similarity": round(similarity, 4),
            "distance": round(distance, 4),
            "message": "✅ تطابق" if verified else "❌ لا يوجد تطابق",
        }
