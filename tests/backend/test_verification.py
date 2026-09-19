import io
from unittest.mock import AsyncMock, patch


def test_verify_face_no_face(client):
    with patch(
        "app.services.face_service.FaceService.encode",
        new=AsyncMock(return_value=[]),
    ):
        r = client.post(
            "/api/verification/face",
            files={"selfie": ("s.jpg", io.BytesIO(b"data"), "image/jpeg")},
        )
    assert r.status_code == 422


def test_verify_face_ok(client):
    with patch(
        "app.services.face_service.FaceService.encode",
        new=AsyncMock(return_value=[0.1, 0.2, 0.3]),
    ):
        r = client.post(
            "/api/verification/face",
            files={"selfie": ("s.jpg", io.BytesIO(b"data"), "image/jpeg")},
        )
    assert r.status_code == 200
    assert r.json()["encoding"] == [0.1, 0.2, 0.3]