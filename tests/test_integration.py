
from src.services.rate_limiter import RateLimiter


class DummyMatcher:
    def __init__(self, matched=True):
        self._matched = matched
    def compare(self, a, b):
        return {"matched": self._matched, "similarity": 0.9}


def _make_engine(antispoof, matcher, limiter):
    """محاكاة VerificationEngine دون الحاجة لتحميل بقية التبعيات."""
    from src.services.audit_log import log_attempt

    class Engine:
        def __init__(self):
            self.antispoof = antispoof
            self.face_matcher = matcher
            self.rate_limiter = limiter

        def verify_user(self, selfie, nid, *, user_id=None, ip=None):
            rl = self.rate_limiter.check(user_id=user_id, ip=ip)
            if not rl.allowed:
                return {"status": "RATE_LIMITED",
                        "retry_after": round(rl.retry_after, 2)}
            asr = self.antispoof.check(selfie)
            if asr["decision"] == "REJECT":
                return {"status": "REJECTED", "code": "SPOOF_DETECTED"}
            if asr["decision"] == "REVIEW":
                return {"status": "MANUAL_REVIEW"}
            m = self.face_matcher.compare(selfie, nid)
            if not m["matched"]:
                return {"status": "REJECTED", "code": "FACE_MISMATCH"}
            return {"status": "VERIFIED",
                    "antispoofing_score": asr["antispoofing_score"]}
    return Engine()


def test_full_happy_path(antispoof_service, real_face_bytes):
    eng = _make_engine(
        antispoof_service, DummyMatcher(True),
        RateLimiter(user_limit=10, ip_limit=10),
    )
    r = eng.verify_user(real_face_bytes, real_face_bytes,
                       user_id="u", ip="1.1.1.1")
    assert r["status"] in ("VERIFIED", "MANUAL_REVIEW")


def test_spoof_short_circuits_face_match(antispoof_service, corrupt_bytes):
    eng = _make_engine(
        antispoof_service, DummyMatcher(True),
        RateLimiter(user_limit=10, ip_limit=10),
    )
    r = eng.verify_user(corrupt_bytes, corrupt_bytes,
                       user_id="u", ip="1.1.1.1")
    assert r["status"] == "REJECTED"
    assert r["code"] == "SPOOF_DETECTED"


def test_rate_limit_blocks_before_model(antispoof_service, real_face_bytes):
    eng = _make_engine(
        antispoof_service, DummyMatcher(True),
        RateLimiter(user_window=60, user_limit=1, ip_window=60, ip_limit=100),
    )
    assert eng.verify_user(real_face_bytes, real_face_bytes,
                           user_id="u", ip="1.1.1.1")["status"] != "RATE_LIMITED"
    r = eng.verify_user(real_face_bytes, real_face_bytes,
                       user_id="u", ip="1.1.1.1")
    assert r["status"] == "RATE_LIMITED"
    assert "retry_after" in r
