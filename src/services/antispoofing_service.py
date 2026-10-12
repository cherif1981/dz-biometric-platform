"""
Anti-Spoofing using MiniFASNetV2 (Silent-Face-Anti-Spoofing).
Falls back to heuristic if model is unavailable.
"""
import os, cv2, numpy as np
from loguru import logger

# ---- Try to load MiniFASNet ----
HAS_MINIFAS = False
_model = None

try:
    import torch
    import sys
    sys.path.insert(0, '/content/Silent-Face-Anti-Spoofing/src')
    from models.MiniFASNet import MiniFASNetV2

    WEIGHTS = '/content/Silent-Face-Anti-Spoofing/resources/anti_spoof_models/2.7_80x80_MiniFASNetV2.pth'
    if os.path.exists(WEIGHTS):
        _model = MiniFASNetV2(conv6_kernel=(5, 5))
        _model.load_state_dict(torch.load(WEIGHTS, map_location='cpu'))
        _model.eval()
        if torch.cuda.is_available():
            _model = _model.cuda()
        HAS_MINIFAS = True
        logger.info("✅ MiniFASNetV2 loaded successfully")
    else:
        logger.warning(f"MiniFASNet weights not found at {WEIGHTS}")
except Exception as e:
    logger.warning(f"MiniFASNet unavailable: {e}")


class AntiSpoofing:
    """Presentation attack detection (print, replay, mask)."""

    def __init__(self, threshold: float = 0.45):
        self.threshold = threshold
        self.model = _model
        self.has_model = HAS_MINIFAS

    def _preprocess(self, img):
        """Crop and normalize for MiniFASNet (80x80)."""
        face = cv2.resize(img, (80, 80))
        face = face[:, :, ::-1].astype(np.float32) / 255.0  # BGR → RGB
        face = np.transpose(face, (2, 0, 1))  # HWC → CHW
        return face

    def _predict(self, img):
        import torch
        tensor = torch.from_numpy(self._preprocess(img)).unsqueeze(0)
        if torch.cuda.is_available():
            tensor = tensor.cuda()
        with torch.no_grad():
            out = self.model(tensor)
            probs = torch.softmax(out, dim=1).cpu().numpy()[0]
        return float(probs[1])  # class 1 = real

    def _heuristic(self, img):
        """Fallback heuristic when model unavailable."""
        gray = cv2.resize(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (256, 256))
        lap = min(float(cv2.Laplacian(gray, cv2.CV_64F).var()) / 500.0, 1.0)
        f = np.fft.fftshift(np.fft.fft2(gray))
        m = np.abs(f)
        h, w = m.shape
        cy, cx = h//2, w//2
        r = min(h, w)//8
        mask = np.ones_like(m, dtype=bool)
        mask[cy-r:cy+r, cx-r:cx+r] = False
        hf = min(float(m[mask].sum() / (m.sum()+1e-9)) * 10.0, 1.0)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        cd = min(float(np.std(hsv[:,:,1])) / 128.0, 1.0)
        return 0.5*lap + 0.3*hf + 0.2*cd

    def check(self, image_bytes: bytes):
        img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            return {"score": 0.0, "is_real": False, "method": "none", "error": "decode_failed"}

        if self.has_model and self.model is not None:
            try:
                score = self._predict(img)
                return {"score": round(score, 4), "is_real": score >= self.threshold,
                        "method": "minifasnet_v2"}
            except Exception as e:
                logger.warning(f"MiniFASNet inference failed: {e}")

        score = self._heuristic(img)
        return {"score": round(score, 4), "is_real": score >= self.threshold,
                "method": "heuristic_fallback"}
