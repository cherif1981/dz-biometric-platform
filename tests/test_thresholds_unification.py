"""Regression tests: thresholds must come from config/thresholds.yaml only."""

import pathlib
import re

import pytest


def test_antispoofing_service_reads_from_thresholds_yaml():
    """الخدمة يجب أن تُطابق YAML (مصدر واحد)."""
    from src.core.thresholds import get_thresholds, reset_cache
    from src.services.antispoofing_service import AntiSpoofingService

    reset_cache()
    t = get_thresholds()
    svc = AntiSpoofingService()

    assert svc.threshold_reject == t.antispoofing_reject, (
        f"service reject={svc.threshold_reject} != yaml reject={t.antispoofing_reject}"
    )
    assert svc.threshold_accept == t.antispoofing_accept, (
        f"service accept={svc.threshold_accept} != yaml accept={t.antispoofing_accept}"
    )


def test_explicit_override_still_works():
    """التجاوز الصريح في الكود يجب أن يعمل (للاختبارات)."""
    from src.services.antispoofing_service import AntiSpoofingService

    svc = AntiSpoofingService(threshold_reject=0.1, threshold_accept=0.9)
    assert svc.threshold_reject == 0.1
    assert svc.threshold_accept == 0.9


def test_security_yaml_has_no_face_threshold():
    """security.yaml يجب ألا يحتوي على face_matching.similarity_threshold."""
    import yaml

    p = pathlib.Path("config/security.yaml")
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    assert "face_matching" not in data, (
        "security.yaml لا يجب أن يحتوي face_matching — العتبة في thresholds.yaml"
    )


def test_no_hardcoded_decision_thresholds_in_services():
    """لا يُسمح بثوابت قرار (reject/accept) hardcoded في الخدمات."""
    for rel in (
        "src/services/antispoofing_service.py",
        "src/services/verification_service.py",
    ):
        p = pathlib.Path(rel)
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        bad = re.findall(r"^THRESHOLD_(?:REJECT|ACCEPT)\s*=\s*[0-9]", text, re.MULTILINE)
        assert not bad, f"{rel} يحتوي ثوابت قرار hardcoded: {bad} — استخدم thresholds.yaml"


def test_readme_thresholds_match_yaml():
    """README يجب أن يعكس قيم YAML الفعلية."""
    from src.core.thresholds import get_thresholds, reset_cache

    reset_cache()
    t = get_thresholds()

    readme = pathlib.Path("README.md")
    if not readme.exists():
        pytest.skip("README.md غير موجود")

    text = readme.read_text(encoding="utf-8")
    for value in (
        str(t.face_similarity),
        str(t.antispoofing_reject),
        str(t.antispoofing_accept),
        str(t.ocr_confidence),
    ):
        assert value in text, f"README لا يذكر العتبة {value} من thresholds.yaml — التوثيق قديم"
