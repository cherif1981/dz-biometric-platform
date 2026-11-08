"""Regression tests for anti-spoofing security contracts."""
import os
import re
import pytest


def test_adapter_old_shape():
    from src.services.antispoofing_adapter import normalize_antispoof_result
    r = normalize_antispoof_result(
        {"antispoofing_score": 0.87, "is_live": True, "decision": "ACCEPT"}
    )
    assert r["score"] == 0.87
    assert r["is_real"] is True


def test_adapter_new_shape():
    from src.services.antispoofing_adapter import normalize_antispoof_result
    r = normalize_antispoof_result({"score": 0.12, "is_real": False})
    assert r["score"] == 0.12
    assert r["is_real"] is False


def test_adapter_none_fails_closed():
    from src.services.antispoofing_adapter import normalize_antispoof_result
    r = normalize_antispoof_result(None)
    assert r["decision"] == "REJECT"
    assert r["is_real"] is False


def test_adapter_unknown_shape_fails_closed():
    from src.services.antispoofing_adapter import normalize_antispoof_result
    r = normalize_antispoof_result({"foo": "bar"})
    assert r["decision"] == "REJECT"


@pytest.mark.parametrize("path", [
    "anti_spoof/decision.py",
    "src/services/antispoofing_service.py",
    "src/modules/liveness/anti_spoofing.py",
])
def test_force_review_guard_present(path):
    if not os.path.exists(path):
        pytest.skip(f"{path} not present")
    src = open(path, encoding="utf-8").read()
    if "ACCEPT" not in src:
        pytest.skip(f"{path} has no ACCEPT branch")
    assert "FORCE_REVIEW" in src, f"{path} missing FORCE_REVIEW guard"


def test_pad_state_verified_not_set_on_load():
    targets = []
    for root, _, files in os.walk("."):
        if "/.git" in root.replace("\\\\", "/"):
            continue
        for f in files:
            if f.endswith(".py") and ("state" in f or "pad" in f):
                targets.append(os.path.join(root, f))
    if not targets:
        pytest.skip("no PADState file found")
    for p in targets:
        src = open(p, encoding="utf-8").read()
        if "PADState.VERIFIED" not in src:
            continue
        for m in re.finditer(r"def\s+(load\w*|__init__)\b[\s\S]{0,800}", src):
            body = m.group(0)
            assert "PADState.VERIFIED" not in body, (
                f"{p}: VERIFIED set inside {m.group(1)}"
            )


# ── PR #2: PADState.VERIFIED & liveness/decision guards ──────────────

def test_pad_state_verified_gated_on_model_verified():
    """VERIFIED must only be set when MODEL_VERIFIED=true, never on load alone."""
    path = "src/services/antispoofing_service.py"
    src = open(path, encoding="utf-8").read()
    # Old vulnerable pattern must be gone
    assert "PADState.VERIFIED if self.session is not None" not in src, (
        "VERIFIED still set unconditionally on session load"
    )
    # LOADED state must exist
    assert '"LOADED"' in src, "PADState.LOADED missing"
    # VERIFIED must be gated on MODEL_VERIFIED
    assert "elif MODEL_VERIFIED:" in src, "MODEL_VERIFIED gate missing"


def test_liveness_anti_spoofing_has_force_review():
    path = "src/modules/liveness/anti_spoofing.py"
    if not os.path.exists(path):
        pytest.skip(f"{path} not present")
    src = open(path, encoding="utf-8").read()
    assert "FORCE_REVIEW" in src, "liveness/anti_spoofing.py missing FORCE_REVIEW guard"
    assert "MODEL_VERIFIED" in src, "liveness/anti_spoofing.py missing MODEL_VERIFIED gate"


def test_liveness_guard_behavior():
    """Simulate wrapper logic: spoof=True -> REJECT, else FORCE_REVIEW unless MODEL_VERIFIED."""
    import functools
    def make(cls, force_review, model_verified):
        _orig = cls.check
        @functools.wraps(_orig)
        def w(self, *a, **kw):
            r = _orig(self, *a, **kw)
            if isinstance(r, dict):
                if r.get("spoof") is True:
                    r["decision"] = "REJECT"
                elif force_review or not model_verified:
                    r["decision"] = "FORCE_REVIEW"
                else:
                    r["decision"] = "ACCEPT"
            return r
        cls.check = w
    class Fake:
        def check(self): return {"spoof": False, "score": 0.95, "error": None}
    make(Fake, True, False)
    assert Fake().check()["decision"] == "FORCE_REVIEW"
    class Fake2:
        def check(self): return {"spoof": False, "score": 0.95, "error": None}
    make(Fake2, False, True)
    assert Fake2().check()["decision"] == "ACCEPT"
    class Fake3:
        def check(self): return {"spoof": True, "score": 0.1, "error": None}
    make(Fake3, False, True)
    assert Fake3().check()["decision"] == "REJECT"


def test_decision_policy_gated_on_model_verified():
    """POLICY must not become TWO_THRESHOLD unless MODEL_VERIFIED=true."""
    path = "anti_spoof/decision.py"
    if not os.path.exists(path):
        pytest.skip(f"{path} not present")
    src = open(path, encoding="utf-8").read()
    assert "MODEL_VERIFIED" in src, "decision.py missing MODEL_VERIFIED gate"
    assert "or not MODEL_VERIFIED" in src, "POLICY not gated on MODEL_VERIFIED"
