from __future__ import annotations

import cv2
import numpy as np

PREPROCESS_VERSION = "v2"
_INPUT_SIZE = (80, 80)


def preprocess_bgr(image_bgr: np.ndarray, size: tuple[int, int] = _INPUT_SIZE) -> np.ndarray:
    if image_bgr.dtype != np.uint8 or image_bgr.ndim != 3 or image_bgr.shape[2] != 3:
        raise ValueError(f"unexpected image: dtype={image_bgr.dtype} shape={image_bgr.shape}")
    img = cv2.resize(image_bgr, size)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = img.astype(np.float32)
    img = np.transpose(img, (2, 0, 1))[None, ...]
    return np.ascontiguousarray(img)
