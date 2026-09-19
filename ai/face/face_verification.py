import numpy as np


def verify_faces(enc1: list, enc2: list, tolerance: float = 0.6) -> dict:
    if not enc1 or not enc2:
        return {"match": False, "distance": None, "confidence": 0.0}
    a = np.array(enc1)
    b = np.array(enc2)
    distance = float(np.linalg.norm(a - b))
    return {
        "match": distance <= tolerance,
        "distance": distance,
        "confidence": max(0.0, 1.0 - distance),
    }