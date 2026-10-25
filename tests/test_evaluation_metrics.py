"""Unit tests for FAR/FRR/APCER/BPCER computation."""
import pytest
from evaluation.metrics import (
    ConfusionCounts, PADCounts, wilson_ci,
    compute_verification_metrics, roc_points,
)


def test_far_frr_hand_computed():
    # 100 genuine: 95 accepted, 5 rejected → FRR = 5%
    # 100 impostor: 2 accepted, 98 rejected → FAR = 2%
    c = ConfusionCounts(tp=95, fn=5, fp=2, tn=98)
    assert c.frr == pytest.approx(0.05)
    assert c.far == pytest.approx(0.02)


def test_far_frr_empty_safe():
    c = ConfusionCounts()
    assert c.far == 0.0
    assert c.frr == 0.0


def test_apcer_bpcer():
    # 50 attacks, 1 accepted → APCER = 2%
    # 200 bona fide, 10 rejected → BPCER = 5%
    p = PADCounts(attack_total=50, attack_accepted=1,
                  bona_fide_total=200, bona_fide_rejected=10)
    assert p.apcer == pytest.approx(0.02)
    assert p.bpcer == pytest.approx(0.05)


def test_wilson_ci_bounds():
    lo, hi = wilson_ci(0, 100)
    assert lo == 0.0
    assert 0 < hi < 0.05
    lo, hi = wilson_ci(50, 100)
    assert 0.3 < lo < 0.5 < hi < 0.7


def test_verification_metrics_threshold():
    scores = [(0.9, True), (0.8, True), (0.4, True),  # genuine
              (0.85, False), (0.2, False), (0.1, False)]  # impostor
    c = compute_verification_metrics(scores, threshold=0.5)
    # genuine accepted: 0.9, 0.8 → TP=2; 0.4 rejected → FN=1
    # impostor accepted: 0.85 → FP=1; 0.2,0.1 rejected → TN=2
    assert c.tp == 2 and c.fn == 1 and c.fp == 1 and c.tn == 2


def test_roc_points_monotonic_far():
    """ROC convention: thresholds descending → FAR non-decreasing."""
    scores = [(0.9, True)] * 50 + [(0.1, False)] * 50
    roc = roc_points(scores, steps=10)
    fars = [p["FAR"] for p in roc]
    # Thresholds from hi to lo → FAR must be non-decreasing
    assert all(fars[i] <= fars[i+1] + 1e-9 for i in range(len(fars)-1)), \
        f"FAR not monotonic increasing: {fars}"
    # Endpoints: first point = strictest (FAR=0), last = loosest (FAR=1)
    assert fars[0] == pytest.approx(0.0)
    assert fars[-1] == pytest.approx(1.0)
