"""
Calibrate face match threshold using synthetic test embeddings.
In production, replace with real labeled data (genuine vs impostor pairs).
"""
import numpy as np
from loguru import logger


def calibrate_threshold(genuine_scores, impostor_scores, target_far=0.01):
    """
    Find threshold that achieves target False Acceptance Rate (FAR).
    genuine_scores: list of similarity scores for genuine pairs
    impostor_scores: list of similarity scores for impostor pairs
    target_far: desired max false acceptance rate (e.g., 0.01 = 1%)
    """
    impostor_scores = sorted(impostor_scores, reverse=True)
    idx = int(len(impostor_scores) * target_far)
    threshold = impostor_scores[min(idx, len(impostor_scores)-1)]

    tp = sum(1 for s in genuine_scores if s >= threshold)
    fn = len(genuine_scores) - tp
    frr = fn / len(genuine_scores) if genuine_scores else 0

    return {
        "threshold": round(threshold, 4),
        "far_target": target_far,
        "frr_at_target": round(frr, 4),
        "n_genuine": len(genuine_scores),
        "n_impostor": len(impostor_scores),
    }


if __name__ == "__main__":
    np.random.seed(42)
    genuine = np.random.normal(0.65, 0.10, 500).clip(0, 1).tolist()
    impostor = np.random.normal(0.25, 0.10, 500).clip(0, 1).tolist()

    print("=" * 60)
    print("📊 Threshold Calibration Report")
    print("=" * 60)

    for target in [0.001, 0.01, 0.05, 0.10]:
        r = calibrate_threshold(genuine, impostor, target_far=target)
        print(f"\nFAR target={target}:")
        print(f"  → threshold    = {r['threshold']}")
        print(f"  → FRR at target= {r['frr_at_target']}")

    final = calibrate_threshold(genuine, impostor, target_far=0.01)
    print(f"\n✅ Recommended FACE_MATCH_THRESHOLD={final['threshold']}")
