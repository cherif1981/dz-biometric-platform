import io

import pytest
from fastapi.testclient import TestClient

from main import app  # ai/main.py

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["service"] == "ai"


def test_face_compare_endpoint():
    e = [0.1] * 128
    r = client.post("/face/compare", json={"encoding1": e, "encoding2": e})
    assert r.status_code == 200
    assert r.json()["match"] is True


def test_process_invalid_image():
    r = client.post(
        "/process",
        files={"file": ("bad.jpg", io.BytesIO(b"not-an-image"), "image/jpeg")},
    )
    assert r.status_code == 400