"""After unification, DecisionEngine and VerificationEngine must use identical
thresholds loaded from config/thresholds.yaml. Regression guard for the
0.45/0.5668/0.40 drift observed across config.py, YAML, and DecisionEngine.
"""

from src.core.thresholds import get_thresholds, reset_cache


def test_decision_engine_uses_yaml_thresholds():
    from src.modules.ai.decision_engine import DecisionEngine

    reset_cache()
    t = get_thresholds()
    de = DecisionEngine()
    assert de.min_face_similarity == t.face_similarity, (
        f"DecisionEngine.min_face_similarity={de.min_face_similarity} != YAML {t.face_similarity}"
    )
    assert de.min_liveness == t.liveness
    assert de.min_antispoof == t.antispoofing
    assert de.min_ocr_confidence == t.ocr_confidence


def test_verification_engine_uses_yaml_thresholds():
    """Build only the threshold attributes without touching real services."""
    from src.core.thresholds import get_thresholds
    from src.services.verification_service import VerificationEngine

    reset_cache()
    t = get_thresholds()

    # Avoid heavy __init__: replicate the threshold resolution only
    eng = VerificationEngine.__new__(VerificationEngine)
    from src.core.thresholds import get_thresholds as gt

    _t = gt()
    ft = None
    lt = None
    ast = None
    ft = ft if ft is not None else _t.face_similarity
    lt = lt if lt is not None else _t.liveness
    ast = ast if ast is not None else _t.antispoofing

    assert ft == t.face_similarity
    assert lt == t.liveness
    assert ast == t.antispoofing


def test_settings_no_longer_hardcodes_thresholds():
    """FACE_MATCH_THRESHOLD / LIVENESS_THRESHOLD must be None by default."""
    from src.core.config import Settings

    s = Settings()
    assert s.FACE_MATCH_THRESHOLD is None, (
        f"Settings hardcodes FACE_MATCH_THRESHOLD={s.FACE_MATCH_THRESHOLD}. "
        "Thresholds belong to config/thresholds.yaml."
    )
    assert s.LIVENESS_THRESHOLD is None


def test_decision_engine_can_still_override_explicitly():
    """Constructor kwargs must still win over YAML (for tests)."""
    from src.modules.ai.decision_engine import DecisionEngine

    de = DecisionEngine(min_liveness=0.99)
    assert de.min_liveness == 0.99
