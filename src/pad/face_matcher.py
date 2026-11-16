"""InsightFace matcher with upscale fallback for small/aligned crops."""
from __future__ import annotations

import base64
import io
from typing import Optional

import numpy as np
from PIL import Image

_app = None


def _get_app():
    global _app
    if _app is None:
        from insightface.app import FaceAnalysis
        _app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
        _app.prepare(ctx_id=0, det_size=(640, 640))
    return _app


def _decode(x) -> np.ndarray:
    if isinstance(x, np.ndarray):
        return x
    if isinstance(x, Image.Image):
        return np.array(x.convert("RGB"))
    s = str(x)
    if s.startswith("data:"):
        s = s.split(",", 1)[-1]
    return np.array(Image.open(io.BytesIO(base64.b64decode(s))).convert("RGB"))


def _largest_face(faces):
    if not faces:
        return None
    return max(faces, key=lambda f: (f.bbox[2]-f.bbox[0])*(f.bbox[3]-f.bbox[1]))


def _embed(img) -> Optional[np.ndarray]:
    import cv2
    arr = _decode(img)
    if arr.ndim == 2:
        arr = np.stack([arr]*3, axis=-1)
    bgr = arr[:, :, ::-1].astype(np.uint8)

    # محاولة 1: كشف عادي
    faces = _get_app().get(bgr)
    face = _largest_face(faces)
    if face is not None:
        return face.normed_embedding

    # محاولة 2: تكبير الصور الصغيرة (LFW ~125x94)
    h, w = bgr.shape[:2]
    if h < 256 or w < 256:
        scale = max(256/h, 256/w, 2.0)
        up = cv2.resize(bgr, (int(w*scale), int(h*scale)), interpolation=cv2.INTER_CUBIC)
        faces = _get_app().get(up)
        face = _largest_face(faces)
        if face is not None:
            return face.normed_embedding

    # محاولة 3: استخدام الصورة كقص وجه مع محاولة إيجاد المعالم (LFW مقصوصة مسبقًا)
    try:
        from insightface.utils import face_align
        # نضيف هامشًا أبيض حول الصورة، فقد تعمل مع الكاشف
        pad = int(max(h, w) * 0.3)
        padded = cv2.copyMakeBorder(bgr, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=(255,255,255))
        faces = _get_app().get(padded)
        face = _largest_face(faces)
        if face is not None:
            return face.normed_embedding
    except Exception:
        pass
    return None


def similarity(a, b) -> Optional[float]:
    ea, eb = _embed(a), _embed(b)
    if ea is None or eb is None:
        return None
    return float(max(0.0, min(1.0, np.dot(ea, eb))))
