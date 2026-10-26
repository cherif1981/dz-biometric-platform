import pytest

from src.core.thresholds import get_thresholds, reset_cache
from src.services.antispoofing_service import AntiSpoofingService


def test_real_face_is_accepted_or_reviewed(antispoof_service, real_face_bytes):
    r = antispoof_service.check(real_face_bytes)
    assert r["decision"] in ("ACCEPT", "REVIEW"), f"face rejected: {r}"
    assert r["is_live"] == (r["decision"] == "ACCEPT")
    assert 0.0 <= r["antispoofing_score"] <= 1.0


def test_corrupt_image_is_rejected_fail_closed(antispoof_service, corrupt_bytes):
    r = antispoof_service.check(corrupt_bytes)
    assert r["decision"] == "REJECT"
    assert r["is_live"] is False
    assert r["antispoofing_score"] == 0.0


def test_blank_image_is_rejected(antispoof_service, blank_image_bytes):
    r = antispoof_service.check(blank_image_bytes)
    assert r["decision"] == "REJECT"
    assert r["is_live"] is False


def test_custom_thresholds_are_used_not_module_constants(real_face_bytes):
    """يمنع عودة علة shadowing: العتبات المخصصة يجب أن تُطبَّق."""
    svc = AntiSpoofingService(threshold_reject=0.01, threshold_accept=0.999)
    r = svc.check(real_face_bytes)
    # بما أن درجة لينا ~0.99، يجب أن تقع في REVIEW مع العتبة 0.999
    assert r["decision"] == "REVIEW", f"custom thresholds ignored: {r}"


def test_invalid_thresholds_raise():
    with pytest.raises((AssertionError, ValueError)):
        AntiSpoofingService(threshold_reject=0.8, threshold_accept=0.2)


def test_three_decision_bands_are_consistent(antispoof_service, real_face_bytes):
    reset_cache()
    t = get_thresholds()
    THRESHOLD_REJECT = t.antispoofing_reject
    THRESHOLD_ACCEPT = t.antispoofing_accept
    score = antispoof_service.check(real_face_bytes)["antispoofing_score"]
    if score < THRESHOLD_REJECT:
        expected = "REJECT"
    elif score >= THRESHOLD_ACCEPT:
        expected = "ACCEPT"
    else:
        expected = "REVIEW"
    assert antispoof_service.check(real_face_bytes)["decision"] == expected
