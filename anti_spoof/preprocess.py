"""Anti-spoofing preprocessing for MiniFASNetV2 family.

CRITICAL: model expects [0, 255] BGR (NOT [0, 1]). Division by 255
causes output collapse to p[2] ~ 0.99 for ALL inputs.

Class order: [print, live, replay] -> liveness = p[1].
"""
import cv2
import numpy as np

INPUT_SIZE = (80, 80)
INPUT_NAME = "input"
LIVE_INDEX = 1


def preprocess(image_bgr: np.ndarray) -> np.ndarray:
    img = cv2.resize(image_bgr, INPUT_SIZE).astype(np.float32)
    return np.transpose(img, (2, 0, 1))[None]


def liveness_from_output(logits: np.ndarray) -> float:
    e = np.exp(logits - logits.max())
    return float((e / e.sum())[LIVE_INDEX])
