"""كشف الوجه باستخدام InsightFace"""
import cv2
from insightface.app import FaceAnalysis
from ai.face.config import MODEL_NAME, DET_SIZE

_app = None


def get_app():
    """نسخة واحدة من النموذج (singleton)"""
    global _app
    if _app is None:
        _app = FaceAnalysis(name=MODEL_NAME, providers=['CPUExecutionProvider'])
        _app.prepare(ctx_id=0, det_size=DET_SIZE)
    return _app


def detect_faces(image_path):
    """كشف جميع الوجوه في الصورة"""
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"لم يتم تحميل الصورة: {image_path}")
    return img, get_app().get(img)


def get_best_face(faces):
    """اختيار أفضل وجه (الأكبر مساحة)"""
    if not faces:
        return None
    return max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))


def crop_face(img, face, margin=20):
    """قص الوجه مع هامش"""
    x1, y1, x2, y2 = face.bbox.astype(int)
    h, w = img.shape[:2]
    x1 = max(0, x1 - margin)
    y1 = max(0, y1 - margin)
    x2 = min(w, x2 + margin)
    y2 = min(h, y2 + margin)
    return img[y1:y2, x1:x2]