import io
import numpy as np
from PIL import Image


def check_quality(image_bytes: bytes) -> dict:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    arr = np.asarray(img).astype(np.float32)

    h, w, _ = arr.shape
    issues: list[str] = []

    if min(h, w) < 480:
        issues.append("low_resolution")

    gray = arr.mean(axis=2)
    brightness = gray.mean()
    if brightness < 50:
        issues.append("too_dark")
    elif brightness > 220:
        issues.append("too_bright")

    # Blur: variance of Laplacian (approximate)
    lap = (
        -4 * gray[1:-1, 1:-1]
        + gray[:-2, 1:-1] + gray[2:, 1:-1]
        + gray[1:-1, :-2] + gray[1:-1, 2:]
    )
    if lap.var() < 80:
        issues.append("blurry")

    return {"ok": len(issues) == 0, "issues": issues,
            "brightness": float(brightness), "sharpness": float(lap.var())}