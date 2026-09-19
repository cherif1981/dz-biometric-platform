from typing import List, Tuple

import numpy as np


def detect_fields(img: np.ndarray) -> List[Tuple[int, int, int, int]]:
    """Detect ROI of text fields (placeholder)."""
    h, w = img.shape[:2]
    # Split card into 3 horizontal bands (rough heuristic)
    return [
        (0, 0, w, h // 3),
        (0, h // 3, w, 2 * h // 3),
        (0, 2 * h // 3, w, h),
    ]