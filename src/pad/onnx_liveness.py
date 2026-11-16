"""ONNX liveness checker — anti-spoof-mn3 (OpenVINO).
Preprocessing: RGB, [0,255] → resize → /255 → (x-0.5)/0.5 = [-1,1].
"""
from __future__ import annotations

import base64
import io
from pathlib import Path

import numpy as np
from PIL import Image

_session = None
DEFAULT_WEIGHTS = Path(__file__).parent.parent.parent / "weights" / "anti-spoof-mn3.onnx"


def _get_session(weights_path: str | None = None):
    global _session
    if _session is None:
        import onnxruntime as ort
        path = weights_path or str(DEFAULT_WEIGHTS)
        if not Path(path).exists():
            raise FileNotFoundError(f"PAD weights missing: {path}")
        _session = ort.InferenceSession(path, providers=["CPUExecutionProvider"])
    return _session


def _decode(x) -> Image.Image:
    if isinstance(x, Image.Image):
        return x.convert("RGB")
    if isinstance(x, np.ndarray):
        return Image.fromarray(x).convert("RGB")
    s = str(x)
    if s.startswith("data:"):
        s = s.split(",", 1)[-1]
    try:
        raw = base64.b64decode(s, validate=True)
    except Exception as e:
        raise ValueError(f"invalid base64 selfie: {e}") from e
    return Image.open(io.BytesIO(raw)).convert("RGB")


def predict_liveness(image, weights_path: str | None = None) -> float:
    """0..1 — أعلى = أكثر حيوية. preprocessing: pm1 ([-1,1])."""
    import cv2
    session = _get_session(weights_path)
    inp = session.get_inputs()[0]
    h_in, w_in = int(inp.shape[2]), int(inp.shape[3])

    arr = np.array(_decode(image))  # RGB, [0,255]
    x = cv2.resize(arr, (w_in, h_in)).astype(np.float32) / 255.0
    x = (x - 0.5) / 0.5  # → [-1, 1]
    x = np.transpose(x, (2, 0, 1))[None, ...]

    out = session.run(None, {inp.name: x})[0][0]
    probs = np.exp(out - out.max()) / np.exp(out - out.max()).sum()
    return float(probs[1])  # [fake, real] → real


def warm_up(weights_path: str | None = None):
    try:
        _get_session(weights_path)
        return True, "ok"
    except Exception as e:
        return False, str(e)
