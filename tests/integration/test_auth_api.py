from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_login_demo_is_rejected():
    """الثغرة أُغلقت: demo/demo يجب أن يُرفض، ولا يصدر أي توكن."""
    r = client.post("/api/v1/auth/login", data={"username": "demo", "password": "demo"})
    assert r.status_code == 401, f"demo/demo must be rejected, got {r.status_code}"
    body = r.json()
    assert "access_token" not in body, "no token should be issued"
    assert "detail" in body

def test_login_bad():
    r = client.post("/api/v1/auth/login", data={"username": "x", "password": "y"})
    assert r.status_code == 401


def test_health():
    assert client.get("/health").json()["status"] == "ok"