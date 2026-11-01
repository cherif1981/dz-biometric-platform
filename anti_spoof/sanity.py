"""sanity_check — يرفض المدخلات غير المنطقية (ضوضاء/أسود/أبيض/ضبابية)."""
import cv2


def sanity_check(img_bgr):
    """يعيد (ok: bool, reason: str)."""
    if img_bgr is None or img_bgr.size == 0:
        return False, "empty_image"
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    if float(gray.std()) < 15:
        return False, f"low_contrast(std={gray.std():.1f})"
    lap = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    if lap > 2000:
        return False, f"high_texture(lap={lap:.0f})_noise"
    if lap < 10:
        return False, f"low_texture(lap={lap:.0f})_blur"
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).flatten()
    hist /= hist.sum()
    if int((hist > 0.01).sum()) > 50:
        return False, "uniform_histogram_noise"
    return True, "OK"
