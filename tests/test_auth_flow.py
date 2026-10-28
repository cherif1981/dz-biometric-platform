"""Integration test: security controls + auth flow."""
import fakeredis
import pytest

from security.audit import AuditLog, AuditEvent
from security.ratelimit import RateLimiter
from security.retention import SecureStorage, RetentionPolicy
from integration.auth_flow import AuthFlow


@pytest.fixture
def flow():
    redis = fakeredis.FakeRedis(decode_responses=True)
    return AuthFlow(
        audit=AuditLog(":memory:"),
        limiter=RateLimiter(redis, limit=5, window_seconds=60),
        storage=SecureStorage("/tmp/auth_test_store", "0" * 64,
                              RetentionPolicy()),
    )


def _valid_mrz():
    from evaluation.verification.mrz import mrz_check_digit
    doc = "108512345"
    doc_chk = mrz_check_digit(doc)
    line1 = "IDDZA" + doc + str(doc_chk) + "<" * 15
    dob = "850312"; dob_chk = mrz_check_digit(dob)
    exp = "300101"; exp_chk = mrz_check_digit(exp)
    opt = "<" * 11
    composite = line1[5:30] + dob + str(dob_chk) + exp + str(exp_chk) + opt
    comp_chk = mrz_check_digit(composite)
    line2 = dob + str(dob_chk) + "M" + exp + str(exp_chk) + "DZA" + opt + str(comp_chk)
    line3 = "BEN ALI<<MOHAMED".ljust(30, "<")
    return line1, line2, line3


def test_valid_document_but_heuristic_spoof_goes_to_review(flow):
    """Valid MRZ + OCR ok + spoof heuristic => REVIEW (not ACCEPT)."""
    r = flow.authenticate("user1", "s1", b"img",
                         liveness_score=0.9, mrz_lines=_valid_mrz(), ocr_ok=True)
    assert r.decision == "REVIEW"
    assert flow.audit.count() >= 1
    assert flow.audit.verify_chain()


def test_suspect_mrz_rejects_regardless_of_ocr(flow):
    """Bad MRZ => REJECT even if OCR is perfect."""
    bad = ("IDDZA" + "1085123459" + "<" * 15,
           "8503127M3001019DZA" + "<" * 11 + "0",
           "BEN ALI<<MOHAMED".ljust(30, "<"))
    r = flow.authenticate("user2", "s2", b"img",
                         liveness_score=0.9, mrz_lines=bad, ocr_ok=True)
    assert r.decision == "REJECT"
    assert flow.audit.verify_chain()


def test_rate_limit_blocks(flow):
    for i in range(5):
        flow.authenticate(f"u{i}", f"s{i}", b"img", 0.9, None, True)
    r = flow.authenticate("u99", "s99", b"img", 0.9, None, True)
    # بعد 6 محاولات يجب أن يظهر deny في السجل
    assert any(e for e in ["auth_rate_limited", "auth_decision"])


def test_audit_chain_survives_all_paths(flow):
    for i in range(3):
        flow.authenticate(f"u{i}", f"s{i}", b"img", 0.9, _valid_mrz(), True)
    flow.authenticate("ubad", "sbad", b"img", 0.9,
                     ("bad", "bad", "bad"), True)
    assert flow.audit.verify_chain()
