"""
Guards against regression: the AI report MUST reflect the actual decision.
Previously, _fin() hardcoded VerificationStatus.VERIFIED and referenced an
undefined `_risk_result`, so every report was either misleading or errored.
"""
from unittest.mock import MagicMock
import pytest

from src.services.verification_service import (
    VerificationEngine, VerificationStatus, VerificationResult,
)


def _bare_engine():
    """Engine instance without __init__ (no real services needed)."""
    eng = VerificationEngine.__new__(VerificationEngine)
    eng.report_builder = MagicMock()
    eng.report_builder.build.return_value.to_dict.return_value = {"ok": True}
    eng.db = MagicMock()
    eng.db.log.return_value = 42
    return eng


def _captured_decision(eng):
    """Return the `decision` object passed to report_builder.build()."""
    args, kwargs = eng.report_builder.build.call_args
    dr = kwargs.get("decision_result")
    if dr is None and args:
        dr = args[0]
    return dr


@pytest.mark.parametrize("status", [
    VerificationStatus.VERIFIED,
    VerificationStatus.MANUAL_REVIEW,
    VerificationStatus.REJECTED,
])
def test_report_decision_matches_actual_status(status):
    eng = _bare_engine()
    risk = MagicMock(score=0.3)
    eng._fin(status, 0.7, 0.9, 0.9, 0.9, {}, [], {}, "127.0.0.1", risk_result=risk)

    dr = _captured_decision(eng)
    assert dr is not None, "report_builder.build was not called"
    assert dr.decision == status, (
        f"Report decision {dr.decision!r} != actual status {status!r}. "
        "Regression: hardcoded VERIFIED has returned."
    )
    assert dr.risk is risk


def test_result_status_equals_passed_status():
    eng = _bare_engine()
    r = eng._fin(VerificationStatus.REJECTED, 0.1, 0.2, 0.2, 0.2,
                 {}, ["FACE:0.2"], {}, None)
    assert isinstance(r, VerificationResult)
    assert r.status == VerificationStatus.REJECTED


def test_report_attached_to_result():
    eng = _bare_engine()
    eng.report_builder.build.return_value.to_dict.return_value = {"status": "REJECTED"}
    r = eng._fin(VerificationStatus.REJECTED, 0.1, 0.2, 0.2, 0.2,
                 {}, ["FACE:0.2"], {}, None)
    assert r.ai_report == {"status": "REJECTED"}, "AI report not attached to result"


def test_report_never_verified_when_rejected():
    """The most important regression: REJECTED must never yield VERIFIED report."""
    eng = _bare_engine()
    eng._fin(VerificationStatus.REJECTED, 0.0, 0.0, 0.0, 0.0,
             {}, ["FACE:0.0", "LIVE:0.0"], {}, None)
    dr = _captured_decision(eng)
    assert dr.decision != VerificationStatus.VERIFIED


def test_missing_risk_result_is_not_fatal():
    """Previously `_risk_result` was undefined -> NameError. Must not happen now."""
    eng = _bare_engine()
    r = eng._fin(VerificationStatus.VERIFIED, 0.9, 0.9, 0.9, 0.9,
                 {}, [], {}, None, risk_result=None)
    assert r.ai_report == {"ok": True}
    assert "error" not in r.ai_report
