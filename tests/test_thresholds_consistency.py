import pytest


def test_yaml_values_loaded():
    from src.core.thresholds import get_thresholds, reset_cache
    reset_cache()
    t = get_thresholds()
    assert t.face_similarity == 0.5668
    assert t.liveness == 0.7
    assert t.antispoofing == 0.55
    assert t.ocr_confidence == 0.8


def test_invalid_yaml_rejected(monkeypatch, tmp_path):
    from src.core.thresholds import get_thresholds, reset_cache
    bad = tmp_path / "bad.yaml"
    bad.write_text("face_similarity: 1.5\nliveness: 0.5\nantispoofing: 0.5\nocr_confidence: 0.8\n")
    monkeypatch.setenv("THRESHOLDS_PATH", str(bad))
    reset_cache()
    with pytest.raises(ValueError, match="outside"):
        get_thresholds()


def test_missing_key_rejected(monkeypatch, tmp_path):
    from src.core.thresholds import get_thresholds, reset_cache
    bad = tmp_path / "bad.yaml"
    bad.write_text("face_similarity: 0.5\n")
    monkeypatch.setenv("THRESHOLDS_PATH", str(bad))
    reset_cache()
    with pytest.raises(ValueError, match="missing"):
        get_thresholds()


def test_env_override_applied(monkeypatch):
    from src.core.thresholds import get_thresholds, reset_cache
    monkeypatch.setenv("LIVENESS_THRESHOLD", "0.95")
    reset_cache()
    t = get_thresholds()
    assert t.liveness == 0.95
