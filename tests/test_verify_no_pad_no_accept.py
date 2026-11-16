"""اختبار معيار القبول: لا ACCEPT بدون PAD VERIFIED + face مقبول.

يبني تطبيق FastAPI مصغرًا يحتوي verify router فقط.
لا يعتمد على src.main → لا DB، لا auth، لا ML.
"""
import pytest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.pad.contract import PADResult, PADState, Decision as PADDecision

TINY_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
    "+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


@pytest.fixture
def client():
    from src.api.v1.endpoints.verify import router
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/verify")
    return TestClient(app)


def _fake_pad(state, decision, reasons=("test",)):
    class FakePAD:
        def __init__(self):
            self.state = state
        def evaluate(self, inp):
            return PADResult(
                decision=decision, state=state, liveness=None, threshold=None,
                reasons=reasons, request_id=inp.request_id, source=inp.source,
                model_sha_prefix=None, preprocess_version="test",
            )
    return FakePAD()


def _post(client):
    for path in ("/api/v1/verify/", "/api/v1/verify"):
        r = client.post(path, json={"selfie": TINY_PNG_B64, "document": TINY_PNG_B64})
        if r.status_code != 404:
            return r
    raise AssertionError("verify endpoint not found")


def test_route_exists(client):
    r = _post(client)
    assert r.status_code in (200, 422), r.text[:200]


def test_high_face_but_pad_unavailable_never_accepts(client):
    """الثغرة الأصلية: face=0.99 + PAD UNAVAILABLE. لا ACCEPT."""
    with patch("src.pad.face_matcher.similarity", return_value=0.99), \
         patch("src.services.audit_log.log_attempt", return_value="audit-x"), \
         patch("src.pad.service.get_pad_service", return_value=_fake_pad(
             PADState.UNAVAILABLE, PADDecision.REJECT, ("model not loaded",))):
        r = _post(client)
    data = r.json()
    assert data["decision"] != "ACCEPT", f"VULN: {data}"
    assert data["pad_state"] == "UNAVAILABLE"


def test_high_face_but_pad_attack_rejects(client):
    with patch("src.pad.face_matcher.similarity", return_value=0.99), \
         patch("src.services.audit_log.log_attempt", return_value="audit-x"), \
         patch("src.pad.service.get_pad_service", return_value=_fake_pad(
             PADState.VERIFIED, PADDecision.REJECT, ("below threshold",))):
        r = _post(client)
    data = r.json()
    assert data["decision"] == "REJECT", f"هجوم مر: {data}"


def test_high_face_and_pad_verified_may_accept(client):
    with patch("src.pad.face_matcher.similarity", return_value=0.99), \
         patch("src.services.audit_log.log_attempt", return_value="audit-x"), \
         patch("src.pad.service.get_pad_service", return_value=_fake_pad(
             PADState.VERIFIED, PADDecision.ACCEPT, ("above threshold",))):
        r = _post(client)
    data = r.json()
    assert data["decision"] == "ACCEPT", data
    assert data["pad_state"] == "VERIFIED"
