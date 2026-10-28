"""اختبارات تراجع أمني.

التشغيل: pytest tests/test_security.py -v
يتطلب: pip install -r requirements.txt
"""
import importlib
import json
import os
import sqlite3
import threading

import pytest


@pytest.fixture
def svc(tmp_path, monkeypatch):
    db = tmp_path / "audit.db"
    monkeypatch.setenv("AUDIT_DB", str(db))
    monkeypatch.setenv("HMAC_SECRET", "test-secret")
    monkeypatch.delenv("REDIS_URL", raising=False)

    import audit, dz_service
    importlib.reload(audit)
    importlib.reload(dz_service)
    dz_service.audit = audit
    audit._conn().close()

    from fastapi.testclient import TestClient
    return {"client": TestClient(dz_service.app), "audit": audit,
            "svc": dz_service, "db": str(db)}


def _challenge(svc):
    return svc["client"].post("/challenge").json()


def test_happy_path(svc):
    ch = _challenge(svc)
    r = svc["client"].post("/submit", json={
        "job_id": ch["job_id"], "nonce": ch["nonce"], "image_b64": "face"})
    assert r.status_code == 200
    assert r.json()["decision"] == "ACCEPTED"


def test_nonce_mismatch(svc):
    ch = _challenge(svc)
    r = svc["client"].post("/submit", json={
        "job_id": ch["job_id"], "nonce": "wrong", "image_b64": "face"})
    assert r.status_code == 401


def test_replay_rejected(svc):
    ch = _challenge(svc)
    assert svc["client"].post("/submit", json={
        "job_id": ch["job_id"], "nonce": ch["nonce"], "image_b64": "face"}).status_code == 200
    assert svc["client"].post("/submit", json={
        "job_id": ch["job_id"], "nonce": ch["nonce"], "image_b64": "face"}).status_code == 409


def test_model_crash_terminates(svc):
    ch = _challenge(svc)
    r = svc["client"].post("/submit", json={
        "job_id": ch["job_id"], "nonce": ch["nonce"],
        "image_b64": "face", "failure_mode": "crash"})
    assert r.status_code == 503
    assert "receipt" not in r.json()
    assert svc["svc"].load(ch["job_id"]).state.value == "TERMINATED"


def test_forged_score_ignored(svc):
    ch = _challenge(svc)
    r = svc["client"].post("/submit", json={
        "job_id": ch["job_id"], "nonce": ch["nonce"],
        "image_b64": "face", "failure_mode": "low",
        "client_pad_score": 0.99})
    assert r.status_code == 401


def test_phantom_decision_prevented(svc):
    audit = svc["audit"]
    orig = audit.append_event
    def fail_at_commit(event_type, *a, **kw):
        if event_type == "ACCEPTED":
            raise RuntimeError("simulated audit failure")
        return orig(event_type, *a, **kw)
    audit.append_event = fail_at_commit
    try:
        ch = _challenge(svc)
        r = svc["client"].post("/submit", json={
            "job_id": ch["job_id"], "nonce": ch["nonce"], "image_b64": "face"})
        assert r.status_code == 500
        assert "receipt" not in r.json()
        assert svc["svc"].load(ch["job_id"]).state.value == "TERMINATED"
    finally:
        audit.append_event = orig


def test_concurrent_submit_only_one_succeeds(svc):
    ch = _challenge(svc)
    orig_load = svc["svc"].load
    barrier = threading.Barrier(2)
    def slow_load(jid):
        s = orig_load(jid)
        try: barrier.wait(timeout=5)
        except threading.BrokenBarrierError: pass
        return s
    svc["svc"].load = slow_load
    results = []
    def do():
        r = svc["client"].post("/submit", json={
            "job_id": ch["job_id"], "nonce": ch["nonce"], "image_b64": "face"})
        results.append(r.status_code)
    ts = [threading.Thread(target=do) for _ in range(2)]
    for t in ts: t.start()
    for t in ts: t.join()
    svc["svc"].load = orig_load
    assert results.count(200) == 1, f"expected 1 success, got {results}"
    assert results.count(409) == 1


def test_chain_detects_tampering(svc):
    audit = svc["audit"]
    for i in range(3):
        audit.append_event("TEST", job_id=f"j{i}")
    assert audit.verify_chain()["ok"] is True
    c = sqlite3.connect(svc["db"], timeout=5.0)
    try:
        with c:
            c.execute("DROP TRIGGER IF EXISTS audit_no_update")
            c.execute("UPDATE audit_logs SET decision=\'ACCEPTED\' WHERE id=2")
    finally:
        c.close()
    v = audit.verify_chain()
    assert v["ok"] is False
    assert v["broken_at"] == 2
    assert v["reason"] == "row_hash mismatch"


def test_audit_append_only_triggers(svc):
    audit = svc["audit"]
    audit.append_event("TEST", job_id="j0")
    c = sqlite3.connect(svc["db"], timeout=5.0)
    try:
        with pytest.raises(sqlite3.IntegrityError):
            with c:
                c.execute("UPDATE audit_logs SET decision=\'X\' WHERE id=1")
    finally:
        c.close()
    c = sqlite3.connect(svc["db"], timeout=5.0)
    try:
        with pytest.raises(sqlite3.IntegrityError):
            with c:
                c.execute("DELETE FROM audit_logs WHERE id=1")
    finally:
        c.close()


def test_illegal_transition_blocked(svc):
    s = svc["svc"].Session(job_id="x", nonce="y")
    with pytest.raises(svc["svc"].StateErr):
        s.transition(svc["svc"].PADState.ACCEPTED)
