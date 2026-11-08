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
