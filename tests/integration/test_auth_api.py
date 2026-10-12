from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_login_demo():
    r = client.post("/api/v1/auth/login", data={"username": "demo", "password": "demo"})
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_login_bad():
    r = client.post("/api/v1/auth/login", data={"username": "x", "password": "y"})
    assert r.status_code == 401


def test_health():
    assert client.get("/health").json()["status"] == "ok"