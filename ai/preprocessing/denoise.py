import cv2
import numpy as np


def denoise_image(img: np.ndarray, strength: int = 10) -> np.ndarray:
    """Remove noise using fastNlMeansDenoisingColored."""
    return cv2.fastNlMeansDenoisingColored(img, None, strength, strength, 7, 21)