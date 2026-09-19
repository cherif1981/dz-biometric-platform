from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import torch
import yaml


class CardDetector:
    """Detect the biometric card in an image."""

    def __init__(self, config_path: str = "configs/model_config.yaml"):
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        self.cfg = cfg["detection"]
        self.device = torch.device(self.cfg.get("device", "cpu"))
        self.model = self._load_model()

    def _load_model(self):
        model_path = Path(self.cfg["model_path"])
        if not model_path.exists():
            return None
        return torch.jit.load(str(model_path), map_location=self.device)

    def detect(self, img: np.ndarray) -> Optional[np.ndarray]:
        """Return 4 corner points or None."""
        if self.model is None:
            return self._fallback_contour(img)
        # Placeholder for real inference
        return self._fallback_contour(img)

    def _fallback_contour(self, img: np.ndarray) -> Optional[np.ndarray]:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blur, 50, 150)
        contours, _ = cv2.findContours(
            edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        if not contours:
            return None
        largest = max(contours, key=cv2.contourArea)
        peri = cv2.arcLength(largest, True)
        approx = cv2.approxPolyDP(largest, 0.02 * peri, True)
        if len(approx) == 4:
            return approx.reshape(4, 2).astype(np.float32)
        return None