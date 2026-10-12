import cv2
import numpy as np
from src.modules.document_reader.preprocessing import to_cv2
from src.core.config import settings


class PassiveLiveness:
    """
    Baseline passive liveness heuristic:
    combines texture sharpness + colour stats. Replace with a trained model in production.
    """

    def predict(self, image_bytes: bytes) -> dict:
        img = to_cv2(image_bytes)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Sharpness
        lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()

        # Colour diversity (real faces have richer skin tones)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        sat = hsv[:, :, 1].mean() / 255.0

        # Frequency energy
        f = np.fft.fft2(gray)
        fshift = np.fft.fftshift(f)
        mag = np.log1p(np.abs(fshift))
        high_freq = mag[mag.shape[0]//4:3*mag.shape[0]//4, mag.shape[1]//4:3*mag.shape[1]//4].mean()

        score = (
            0.4 * min(lap_var / 500.0, 1.0)
            + 0.3 * sat
            + 0.3 * min(high_freq / 10.0, 1.0)
        )
        return {
            "is_live": score >= settings.LIVENESS_THRESHOLD,
            "score": float(score),
            "threshold": settings.LIVENESS_THRESHOLD,
        }