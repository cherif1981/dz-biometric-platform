import io

import pytest
from unittest.mock import AsyncMock, patch


@pytest.fixture
def fake_ocr_response():
    return {
        "fields": {
            "nin": "123456789012345678",
            "nom": "BENALI",
            "prenom": "Ahmed",
            "date_naissance": "01/01/1990",
        },
        "validation": {"valid": True, "errors": []},
        "raw_text": "...",
        "face_encoding": None,
    }


def test_upload_document(client, auth_headers, fake_ocr_response):
    with patch(
        "app.services.ocr_service.OCRService.process",
        new=AsyncMock(return_value=fake_ocr_response),
    ):
        r = client.post(
            "/api/documents/upload",
            headers=auth_headers,
            files={"file": ("card.jpg", io.BytesIO(b"fake"), "image/jpeg")},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["nin"] == "123456789012345678"
    assert body["nom"] == "BENALI"
    assert body["prenom"] == "Ahmed"


def test_upload_empty_file(client, auth_headers):
    r = client.post(
        "/api/documents/upload",
        headers=auth_headers,
        files={"file": ("empty.jpg", io.BytesIO(b""), "image/jpeg")},
    )
    assert r.status_code == 400