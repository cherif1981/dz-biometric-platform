import face_recognition
import numpy as np
from typing import List, Dict
from ai.configs.settings import settings

class FaceDetector:
    def detect(self, image: np.ndarray) -> Dict:
        rgb = image[:, :, ::-1]
        locations = face_recognition.face_locations(rgb, model=settings.FACE_MODEL)
        return {
            "count": len(locations),
            "locations": [list(loc) for loc in locations],
        }

    def crop_faces(self, image: np.ndarray) -> List[np.ndarray]:
        rgb = image[:, :, ::-1]
        locations = face_recognition.face_locations(rgb, model=settings.FACE_MODEL)
        crops = []
        for (top, right, bottom, left) in locations:
            h, w = bottom - top, right - left
            pad_h, pad_w = int(h * 0.2), int(w * 0.2)
            top = max(0, top - pad_h)
            bottom = min(image.shape[0], bottom + pad_h)
            left = max(0, left - pad_w)
            right = min(image.shape[1], right + pad_w)
            crops.append(image[top:bottom, left:right])
        return crops
