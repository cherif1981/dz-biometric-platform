import cv2
import numpy as np
from src.modules.document_reader.preprocessing import to_cv2, deskew, normalize


class CardDetector:
    """Detects document region inside the frame and returns the cropped card."""

    def detect(self, image_bytes: bytes) -> dict:
        img = to_cv2(image_bytes)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        h, w = img.shape[:2]
        best = None
        best_area = 0
        for c in contours:
            approx = cv2.approxPolyDP(c, 0.02 * cv2.arcLength(c, True), True)
            if len(approx) == 4:
                area = cv2.contourArea(approx)
                if area > best_area and area > 0.15 * h * w:
                    best_area = area
                    best = approx

        if best is None:
            crop = img
            doc_type = "unknown"
        else:
            crop = self._warp(img, best)
            doc_type = self._guess_type(crop)

        crop = normalize(deskew(crop))
        return {"image": crop, "type": doc_type, "area_ratio": best_area / (h * w)}

    @staticmethod
    def _warp(img: np.ndarray, quad: np.ndarray) -> np.ndarray:
        pts = quad.reshape(4, 2).astype(np.float32)
        s = pts.sum(axis=1)
        d = np.diff(pts, axis=1).ravel()
        rect = np.array([
            pts[np.argmin(s)], pts[np.argmin(d)],
            pts[np.argmax(s)], pts[np.argmax(d)],
        ], dtype=np.float32)
        (tl, tr, br, bl) = rect
        W = int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl)))
        H = int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl)))
        dst = np.array([[0, 0], [W - 1, 0], [W - 1, H - 1], [0, H - 1]], dtype=np.float32)
        M = cv2.getPerspectiveTransform(rect, dst)
        return cv2.warpPerspective(img, M, (W, H))

    @staticmethod
    def _guess_type(crop: np.ndarray) -> str:
        h, w = crop.shape[:2]
        ratio = w / max(h, 1)
        # Algerian ID card / driving license ~ 1.58 (ID-1)
        if 1.45 <= ratio <= 1.75:
            return "id_card"
        if ratio > 1.3:
            return "passport"
        return "unknown"