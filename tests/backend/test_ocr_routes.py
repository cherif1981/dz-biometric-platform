import io
from unittest.mock import AsyncMock, patch


def test_ocr_extract(client, fake_ocr_response if False else None):  # placeholder
    pass


def test_ocr_extract_ok(client):
    fake = {
        "fields": {"nin": "1" * 18},
        "validation": {"valid": True, "errors": []},
        "raw_text": "x",
        "face_encoding": None,
    }
    with patch(
        "app.services.ocr_service.OCRService.process",
        new=AsyncMock(return_value=fake),
    ):
        r = client.post(
            "/api/ocr/extract",
            files={"file": ("card.jpg", io.BytesIO(b"data"), "image/jpeg")},
        )
    assert r.status_code == 200
    assert r.json()["fields"]["nin"] == "1" * 18


def test_ocr_extract_empty(client):
    r = client.post(
        "/api/ocr/extract",
        files={"file": ("e.jpg", io.BytesIO(b""), "image/jpeg")},
    )
    assert r.status_code == 400