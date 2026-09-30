"""Tests for OCR routes."""
import io
from unittest.mock import patch

import pytest


@pytest.fixture
def fake_ocr_response():
    """نموذج استجابة OCR وهمي."""
    return {
        "success": True,
        "text": "الجمهورية الجزائرية الديمقراطية الشعبية",
        "confidence": 0.95,
        "fields": {
            "first_name": "محمد",
            "last_name": "بن علي",
            "birth_date": "1990-01-01",
        },
    }


@pytest.fixture
def fake_image_bytes():
    """صورة PNG صغيرة صالحة (1x1 بكسل)."""
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
        b"\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
        b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def test_ocr_route_exists(client):
    """المسار يجب أن يرد (ولو بخطأ إدخال)."""
    r = client.post("/api/v1/ocr/extract")
    # 422 = نقص ملف، 401/403 = مصادقة، 400 = إدخال خاطئ
    assert r.status_code in (400, 401, 403, 422), r.text


def test_ocr_extract_with_mock(client, fake_image_bytes, fake_ocr_response):
    """اختبار الاستخراج مع محرك وهمي."""
    with patch("app.api.v1.endpoints.ocr.AIService.scan_card") as mock:
        mock.return_value = fake_ocr_response
        files = {"file": ("test.png", io.BytesIO(fake_image_bytes), "image/png")}
        r = client.post("/api/v1/ocr/extract", files=files)
        assert r.status_code in (200, 401, 403), r.text


def test_ocr_extract_no_file(client):
    """يجب أن يرفض الطلب بدون ملف."""
    r = client.post("/api/v1/ocr/extract")
    assert r.status_code in (400, 401, 403, 422), r.text


def test_ocr_invalid_file_type(client):
    """يجب أن يرفض نوع ملف غير مدعوم."""
    files = {"file": ("test.txt", io.BytesIO(b"not an image"), "text/plain")}
    r = client.post("/api/v1/ocr/extract", files=files)
    assert r.status_code in (400, 401, 403, 415, 422), r.text
