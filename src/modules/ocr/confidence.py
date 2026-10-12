def fuse_confidences(*scores: float, weights: list[float] | None = None) -> float:
    if not scores:
        return 0.0
    if weights is None:
        weights = [1.0] * len(scores)
    total_w = sum(weights)
    return sum(s * w for s, w in zip(scores, weights)) / total_w