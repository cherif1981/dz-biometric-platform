import cv2
import numpy as np


class FaceDetector:
    def __init__(self, model: str = "hog"):
        self.model = model

    def detect(self, img: np.ndarray) -> list:
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        try:
            import face_recognition

            return face_recognition.face_locations(rgb, model=self.model)
        except ImportError:
            return []