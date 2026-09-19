import numpy as np


def check_liveness(img: np.ndarray, threshold: float = 0.7) -> dict:
    """Placeholder liveness detection based on image sharpness."""
    gray = np.mean(img, axis=2)
    laplacian_var = float(np.var(gray))
    score = min(laplacian_var / 1000.0, 1.0)
    return {"is_live": score >= threshold, "score": score}