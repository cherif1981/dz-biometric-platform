"""مكافحة الانتحال - MiniFASNet (ONNX) + سياسة قرار ثلاثية."""

import os
import urllib.request

import cv2
import numpy as np
import onnxruntime as ort

try:
    from src.services import metrics as _metrics
except Exception:
    _metrics = None

MODEL_URLS = [
    "https://github.com/yakhyo/face-anti-spoofing/releases/download/weights/MiniFASNetV2.onnx",
]
MODEL_PATH = "/content/models/MiniFASNetV2.onnx"
YUNET_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
YUNET_PATH = "/content/models/face_detection_yunet_2023mar.onnx"
INPUT_SIZE = (80, 80)
SCALE = 2.7
REAL_CLASS_INDEX = 2

# ── عتبات القرار (اضبطها حسب بياناتك) ──
# ما بينهما => مراجعة يدوية


def _download(url, path, min_bytes=1024):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path) and os.path.getsize(path) > min_bytes:
        return
    print("Downloading:", url)
    urllib.request.urlretrieve(url, path)
    print("OK:", path, os.path.getsize(path), "bytes")


def _softmax(x):
    e = np.exp(x - np.max(x, axis=-1, keepdims=True))
    return e / e.sum(axis=-1, keepdims=True)


def _crop_face(img, bbox, scale=SCALE, out_size=INPUT_SIZE):
    x1, y1, x2, y2 = map(int, bbox)
    w, h = x2 - x1, y2 - y1
    if w <= 0 or h <= 0:
        raise ValueError("invalid bbox")
    cx, cy = x1 + w / 2, y1 + h / 2
    nw, nh = w * scale, h * scale
    nx1 = max(0, int(cx - nw / 2))
    ny1 = max(0, int(cy - nh / 2))
    nx2 = min(img.shape[1], int(cx + nw / 2))
    ny2 = min(img.shape[0], int(cy + nh / 2))
    face = img[ny1:ny2, nx1:nx2]
    if face.size == 0:
        raise ValueError("empty crop")
    return cv2.resize(face, out_size)


class YuNetDetector:
    name = "YuNet"

    def __init__(self):
        _download(YUNET_URL, YUNET_PATH, 100_000)
        if hasattr(cv2, "FaceDetectorYN_create"):
            self.model = cv2.FaceDetectorYN_create(
                YUNET_PATH,
                "",
                (320, 320),
                score_threshold=0.6,
                nms_threshold=0.3,
                top_k=5000,
            )
            self.mode = "FaceDetectorYN"
        else:
            self.net = cv2.dnn.readNetFromONNX(YUNET_PATH)
            self.mode = "dnn_raw"

    def detect(self, img):
        h, w = img.shape[:2]
        if self.mode == "FaceDetectorYN":
            self.model.setInputSize((w, h))
            _, faces = self.model.detect(img)
            if faces is None:
                return []
            return [(int(f[0]), int(f[1]), int(f[0] + f[2]), int(f[1] + f[3])) for f in faces]
        blob = cv2.dnn.blobFromImage(img, 1 / 255.0, (w, h), swapRB=False, crop=False)
        self.net.setInput(blob)
        out = self.net.forward()[0]
        bboxes = []
        for row in out:
            if float(row[14]) < 0.6:
                continue
            x, y, bw, bh = row[0] * w, row[1] * h, row[2] * w, row[3] * h
            bboxes.append((int(x), int(y), int(x + bw), int(y + bh)))
        return bboxes


def _verify_model_integrity(model_path: str) -> None:
    """
    يتحقق من SHA256 النموذج ضد القيمة في security.yaml.
    يرفض التشغيل إن كان الملف قد تلاعب به أحد.
    """
    import hashlib
    import pathlib

    expected = None
    yaml_p = pathlib.Path("/content/dz-biometric-platform/config/security.yaml")
    if yaml_p.exists():
        try:
            import yaml

            cfg = yaml.safe_load(yaml_p.read_text(encoding="utf-8")) or {}
            expected = (cfg.get("antispoofing", {}).get("model", {}).get("sha256") or "").strip()
        except Exception:
            pass
    if not expected:
        return  # لا تحقق مُهيَّأ
    h = hashlib.sha256()
    with open(model_path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    actual = h.hexdigest()
    if actual != expected:
        raise RuntimeError(
            f"❌ تلاعب بنموذج مكافحة الانتحال! متوقع: {expected[:16]}..., حصلنا: {actual[:16]}..."
        )


class AntiSpoofingService:
    def __init__(
        self, threshold_reject: float | None = None, threshold_accept: float | None = None
    ):
        # المصدر الوحيد: config/thresholds.yaml عبر get_thresholds()
        if threshold_reject is None or threshold_accept is None:
            from src.core.thresholds import get_thresholds

            t = get_thresholds()
            if threshold_reject is None:
                threshold_reject = t.antispoofing_reject
            if threshold_accept is None:
                threshold_accept = t.antispoofing_accept
        assert 0 < threshold_reject < threshold_accept < 1, (
            f"يجب أن يكون 0 < reject < accept < 1 (حصلنا {threshold_reject}, {threshold_accept})"
        )
        self.threshold_reject = float(threshold_reject)
        self.threshold_accept = float(threshold_accept)
        _download(MODEL_URLS[0], MODEL_PATH, 100_000)
        _verify_model_integrity(MODEL_PATH)
        self.session = ort.InferenceSession(MODEL_PATH, providers=["CPUExecutionProvider"])
        self.input_name = self.session.get_inputs()[0].name
        self.detector = YuNetDetector()
        print(
            f"AntiSpoofingService ready | reject<{self.threshold_reject} "
            f"review<{self.threshold_accept} accept>={self.threshold_accept}"
        )

    def _decide(self, score: float) -> str:
        """يستخدم self.threshold_reject / self.threshold_accept (وليس ثوابت الوحدة)."""
        if score < self.threshold_reject:
            return "REJECT"
        if score >= self.threshold_accept:
            return "ACCEPT"
        return "REVIEW"

    def check(self, image_bytes: bytes) -> dict:
        return self.verify(image_bytes)

    def verify(self, image_bytes: bytes) -> dict:
        # ── فك الترميز ──
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return self._result(0.0, "REJECT", "decode failed", "YuNet")

        # ── اكتشاف الوجه ──
        try:
            faces = self.detector.detect(img)
        except Exception as e:
            return self._result(0.0, "REJECT", f"detector failed: {e}", self.detector.name)
        if not faces:
            return self._result(0.0, "REJECT", "no face", self.detector.name)

        # ── قصّ الوجه ──
        bbox = max(faces, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]))
        try:
            face = _crop_face(img, bbox)
        except Exception as e:
            return self._result(0.0, "REJECT", f"crop failed: {e}", self.detector.name)

        face = cv2.cvtColor(face, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        face = np.expand_dims(np.transpose(face, (2, 0, 1)), 0)

        # ── الاستدلال ──
        try:
            logits = self.session.run(None, {self.input_name: face})[0][0]
        except Exception as e:
            return self._result(0.0, "REJECT", f"inference failed: {e}", self.detector.name)

        probs = _softmax(logits)
        real_score = float(probs[REAL_CLASS_INDEX])
        decision = self._decide(real_score)

        # ── بناء النتيجة ──
        if decision == "ACCEPT":
            reason = "live"
        elif decision == "REVIEW":
            reason = f"borderline score ({real_score:.3f}) - manual review"
        else:
            reason = f"spoof (score={real_score:.3f})"

        return self._result(real_score, decision, reason, self.detector.name)

    def _result(self, score: float, decision: str, reason: str, detector: str) -> dict:
        if _metrics:
            _metrics.record_antispoof_result(decision, score)
        return {
            "is_live": decision == "ACCEPT",  # توافق خلفي
            "decision": decision,  # "ACCEPT" | "REVIEW" | "REJECT"
            "antispoofing_score": float(score),
            "reason": reason,
            "detector": detector,
        }


# ═══════════════════════════════════════════════════════════════════
# توافق خلفي: الكود القديم (verification_service.py) يستورد AntiSpoofing
# ═══════════════════════════════════════════════════════════════════
AntiSpoofing = AntiSpoofingService
