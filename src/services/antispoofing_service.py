"""
Anti-Spoofing using MiniFASNetV2 + MiniFASNetV1SE (Silent-Face-Anti-Spoofing).
Ensemble prediction. Falls back to heuristic if model unavailable.
"""
import sys
from pathlib import Path

import cv2
import numpy as np
from loguru import logger

# ---- Locate Silent-Face-Anti-Spoofing (relative to project root) ----
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_AS_REPO = _PROJECT_ROOT / "models" / "Silent-Face-Anti-Spoofing"
_AS_SRC = _AS_REPO / "src"
_AS_WEIGHTS_DIR = _AS_REPO / "resources" / "anti_spoof_models"

HAS_MINIFAS = False
_models = []

try:
    import torch
    if str(_AS_SRC) not in sys.path:
        sys.path.insert(0, str(_AS_SRC))
    from models.MiniFASNet import MiniFASNetV2, MiniFASNetV1SE

    _MODEL_CONFIGS = [
        ("2.7_80x80_MiniFASNetV2.pth", MiniFASNetV2, (5, 5)),
        ("4_0_0_80x80_MiniFASNetV1SE.pth", MiniFASNetV1SE, (5, 5)),
    ]

    for fname, cls, kernel in _MODEL_CONFIGS:
        wpath = _AS_WEIGHTS_DIR / fname
        if not wpath.exists():
            logger.warning(f"⚠️  Missing weights: {wpath}")
            continue
        m = cls(conv6_kernel=kernel)
        m.load_state_dict(torch.load(str(wpath), map_location="cpu"))
        m.eval()
        _models.append(m)

    if _models:
        HAS_MINIFAS = True
        logger.info(f"✅ Loaded {len(_models)} MiniFASNet model(s)")
    else:
        logger.warning("❌ No weights loaded — falling back to heuristic")
except Exception as e:
    logger.warning(f"MiniFASNet unavailable: {e}")


class AntiSpoofing:
    """Presentation attack detection (print, replay, mask)."""

    def __init__(self, threshold: float = 0.45):
        self.threshold = threshold
        self.models = _models
        self.has_model = HAS_MINIFAS
        self._torch = None
        if self.has_model:
            import torch
            self._torch = torch

    def _preprocess(self, img):
        face = cv2.resize(img, (80, 80))
        face = face[:, :, ::-1].astype(np.float32) / 255.0
        face = np.transpose(face, (2, 0, 1))
        return (face - 0.5) / 0.5

    def _predict_one(self, model, img):
        torch = self._torch
        tensor = torch.from_numpy(self._preprocess(img)).unsqueeze(0).float()
        with torch.no_grad():
            out = model(tensor)
            probs = torch.softmax(out, dim=1).cpu().numpy()[0]
        return float(probs[1])

    def _predict(self, img):
        return float(np.mean([self._predict_one(m, img) for m in self.models]))

    def _heuristic(self, img):
        gray = cv2.resize(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (256, 256))
        lap = min(float(cv2.Laplacian(gray, cv2.CV_64F).var()) / 500.0, 1.0)
        f = np.fft.fftshift(np.fft.fft2(gray))
        m = np.abs(f)
        h, w = m.shape
        cy, cx = h // 2, w // 2
        r = min(h, w) // 8
        mask = np.ones_like(m, dtype=bool)
        mask[cy - r:cy + r, cx - r:cx + r] = False
        hf = min(float(m[mask].sum() / (m.sum() + 1e-9)) * 10.0, 1.0)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        cd = min(float(np.std(hsv[:, :, 1])) / 128.0, 1.0)
        return 0.5 * lap + 0.3 * hf + 0.2 * cd

    def check(self, image_bytes: bytes):
        img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            return {"score": 0.0, "is_real": False, "method": "none",
                    "error": "decode_failed"}

        if self.has_model and self.models:
            try:
                score = self._predict(img)
                return {"score": round(score, 4),
                        "is_real": score >= self.threshold,
                        "method": f"minifasnet_ensemble_x{len(self.models)}"}
            except Exception as e:
                logger.warning(f"MiniFASNet inference failed: {e}")

        score = self._heuristic(img)
        return {"score": round(score, 4),
                "is_real": score >= self.threshold,
                "method": "heuristic_fallback"}
