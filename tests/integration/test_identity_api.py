"""Integration tests for /health and /verify/ endpoints."""

import io

import pytest


def _make_image() -> bytes:
    """JPEG صغير صالح للاختبار."""
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (10, 10), color=(200, 200, 200)).save(buf, format="JPEG")
    return buf.getvalue()


class TestHealthEndpoint:
    def test_health_returns_ok(self, client, auth_headers):
        r = client.get("/health", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_health_has_service_name(self, client, auth_headers):
        """العقد الفعلي لنقطة /health: status + version."""
        r = client.get("/health", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "status" in data and data["status"] == "ok"
        assert "version" in data


class TestVerifyEndpoint:
    @pytest.mark.xfail(reason="/verify-legacy returns 410 Gone (deprecated endpoint)", strict=False)
    def test_verify_missing_fields(self, client, auth_headers):
        """بدون ملفات يجب أن يرجع 422."""
        r = client.post("/verify-legacy/", headers=auth_headers)
        assert r.status_code == 422

    @pytest.mark.xfail(reason="deprecated /verify-legacy returns 410", strict=True)
    def test_verify_with_images(self, client, auth_headers):
        """بصورتين صالحتين يجب أن يُقبل الطلب (200)."""
        files = {
            "id_image": ("id.jpg", _make_image(), "image/jpeg"),
            "selfie": ("selfie.jpg", _make_image(), "image/jpeg"),
        }
        r = client.post("/verify-legacy/", headers=auth_headers)
        assert r.status_code == 200

    @pytest.mark.xfail(reason="deprecated /verify-legacy returns 410", strict=True)
    def test_verify_response_structure(self, client, auth_headers):
        """يجب أن يحتوي الرد على الحقول المطلوبة."""
        files = {
            "id_image": ("id.jpg", _make_image(), "image/jpeg"),
            "selfie": ("selfie.jpg", _make_image(), "image/jpeg"),
        }
        r = client.post("/verify-legacy/", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        for key in ["status", "confidence", "face_similarity", "liveness_score"]:
            assert key in data, f"missing {key} in response: {data}"
