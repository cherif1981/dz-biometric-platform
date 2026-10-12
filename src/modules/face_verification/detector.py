import numpy as np
from insightface.app import FaceAnalysis


class FaceDetector:
    _app: FaceAnalysis | None = None

    @classmethod
    def _instance(cls) -> FaceAnalysis:
        if cls._app is None:
            cls._app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
            cls._app.prepare(ctx_id=-1, det_size=(640, 640))
        return cls._app

    def detect(self, image_bytes_or_array):
        from src.modules.document_reader.preprocessing import to_cv2

        img = to_cv2(bytes(image_bytes_or_array)) if isinstance(image_bytes_or_array, (bytes, bytearray)) else image_bytes_or_array
        faces = self._instance().get(img)
        if not faces:
            return None
        # Largest face
        faces.sort(key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]), reverse=True)
        return faces[0]