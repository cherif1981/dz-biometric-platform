"""Integration tests for identity verification API."""
import io
import pytest
from PIL import Image


def _make_image(size=(400, 300), color=(200, 200, 200)):
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf.read()


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_returns_ok(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"

    def test_health_has_service_name(self, client):
        r = client.get("/health")
        data = r.json()
        assert "service" in data


class TestVerifyEndpoint:
    """Tests for /verify/ endpoint."""

    def test_verify_missing_fields(self, client):
        """Should return 422 without files."""
        r = client.post("/verify/")
        assert r.status_code == 422

    def test_verify_with_images(self, client):
        """Should accept two images."""
        files = {
            "id_image": ("id.jpg", _make_image(), "image/jpeg"),
            "selfie": ("selfie.jpg", _make_image(), "image/jpeg"),
        }
        r = client.post("/verify/", files=files)
        assert r.status_code == 200
        data = r.json()
        assert "status" in data
        assert data["status"] in ("VERIFIED", "REJECTED", "MANUAL_REVIEW")

    def test_verify_response_structure(self, client):
        """Response should have all required fields."""
        files = {
            "id_image": ("id.jpg", _make_image(), "image/jpeg"),
            "selfie": ("selfie.jpg", _make_image(), "image/jpeg"),
        }
        r = client.post("/verify/", files=files)
        data = r.json()
        for key in ["status", "confidence", "face_similarity", "liveness_score"]:
            assert key in data
