import cv2
import numpy as np
from typing import Tuple, Optional
from ai.configs.settings import settings

class CardDetector:
    def detect(self, image: np.ndarray) -> Tuple[np.ndarray, Optional[list]]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blur, 50, 150)
        edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)

        contours, _ = cv2.findContours(
            edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        if not contours:
            return image, None

        h_img, w_img = image.shape[:2]
        best, best_area = None, 0

        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            if h == 0:
                continue
            ratio = w / h
            area_ratio = (w * h) / (w_img * h_img)
            if (settings.CARD_ASPECT_RATIO_MIN < ratio < settings.CARD_ASPECT_RATIO_MAX
                    and area_ratio > settings.CARD_MIN_AREA_RATIO):
                if w * h > best_area:
                    best_area = w * h
                    best = (x, y, w, h)

        if best:
            x, y, w, h = best
            return image[y:y+h, x:x+w], [x, y, w, h]
        return image, None
