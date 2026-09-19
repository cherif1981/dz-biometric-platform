import cv2
import numpy as np


def resize_image(img: np.ndarray, target_width: int = 1000) -> np.ndarray:
    """Resize image keeping aspect ratio."""
    h, w = img.shape[:2]
    if w == target_width:
        return img
    ratio = target_width / w
    new_h = int(h * ratio)
    return cv2.resize(img, (target_width, new_h), interpolation=cv2.INTER_CUBIC)