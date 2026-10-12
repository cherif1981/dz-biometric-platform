import cv2, numpy as np


class LivenessService:
    def __init__(self, threshold=0.50):
        self.threshold = threshold

    def _decode(self, b):
        return cv2.imdecode(np.frombuffer(b, np.uint8), cv2.IMREAD_COLOR)

    def check(self, image_bytes):
        img = self._decode(image_bytes)
        if img is None:
            return {"score": 0.0, "is_live": False, "reason": "decode_failed"}
        gray = cv2.resize(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (256, 256))
        lap = min(float(cv2.Laplacian(gray, cv2.CV_64F).var()) / 500.0, 1.0)
        f = np.fft.fftshift(np.fft.fft2(gray))
        m = np.abs(f)
        h, w = m.shape
        cy, cx = h//2, w//2
        r = min(h, w)//8
        mask = np.ones_like(m, dtype=bool)
        mask[cy-r:cy+r, cx-r:cx+r] = False
        hf = min(float(m[mask].sum() / (m.sum()+1e-9)) * 10.0, 1.0)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        cd = min(float(np.std(hsv[:,:,1])) / 128.0, 1.0)
        score = 0.5*lap + 0.3*hf + 0.2*cd
        return {"score": round(score, 4), "is_live": score >= self.threshold,
                "components": {"lap": lap, "hf": hf, "color": cd}}
