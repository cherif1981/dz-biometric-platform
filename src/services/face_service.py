import cv2, numpy as np
from loguru import logger

try:
    from insightface.app import FaceAnalysis
    HAS_INSIGHT = True
except ImportError:
    HAS_INSIGHT = False
    logger.error("InsightFace not installed — FACE VERIFICATION DISABLED (fail-secure)")


def _detect_providers():
    try:
        import onnxruntime as ort
        avail = ort.get_available_providers()
        if "CUDAExecutionProvider" in avail:
            return ["CUDAExecutionProvider", "CPUExecutionProvider"]
    except Exception:
        pass
    return ["CPUExecutionProvider"]


class FaceService:
    _instance = None

    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if HAS_INSIGHT:
            p = _detect_providers()
            logger.info(f"FaceService providers: {p}")
            self.app = FaceAnalysis(name="buffalo_l", providers=p)
            ctx = 0 if "CUDAExecutionProvider" in p else -1
            self.app.prepare(ctx_id=ctx, det_size=(640, 640))
        else:
            self.app = None
            logger.critical("FaceService running WITHOUT model — all verifications will be REJECTED")

    def _decode(self, b):
        return cv2.imdecode(np.frombuffer(b, np.uint8), cv2.IMREAD_COLOR)

    def _embed(self, img):
        if self.app is None:
            return None
        faces = self.app.get(img)
        if not faces:
            return None
        faces = sorted(faces, key=lambda x: (x.bbox[2]-x.bbox[0])*(x.bbox[3]-x.bbox[1]), reverse=True)
        return faces[0].normed_embedding

    def verify(self, id_bytes, selfie_bytes):
        # FAIL-SECURE: if model missing, always reject
        if self.app is None:
            return {
                "similarity": 0.0,
                "is_match": False,
                "error": "face_model_unavailable",
                "note": "InsightFace not loaded — verification cannot proceed"
            }
        e1 = self._embed(self._decode(id_bytes))
        e2 = self._embed(self._decode(selfie_bytes))
        if e1 is None or e2 is None:
            return {"similarity": 0.0, "is_match": False, "error": "no_face_detected"}
        sim = float(np.dot(e1, e2))
        return {"similarity": sim, "is_match": sim >= 0.45}
