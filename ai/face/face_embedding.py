import numpy as np


class FaceEmbedder:
    def __init__(self, model: str = "large"):
        self.model = model

    def embed(self, img: np.ndarray, location: tuple) -> list:
        try:
            import face_recognition

            rgb = img[:, :, ::-1]
            encodings = face_recognition.face_encodings(
                rgb, [location], model=self.model
            )
            return encodings[0].tolist() if encodings else []
        except ImportError:
            return []