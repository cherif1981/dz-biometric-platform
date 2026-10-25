import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.mark.asyncio
async def test_verify_legacy_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/verify-legacy", json={"dummy": "data"})
    assert r.status_code == 401, f"expected 401, got {r.status_code}: {r.text}"


@pytest.mark.asyncio
async def test_verify_legacy_not_404():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/verify-legacy", json={"dummy": "data"})
    assert r.status_code != 404, "المسار اختفى — راجع التعديل"


@pytest.mark.asyncio
async def test_verify_legacy_rejects_forged_scores():
    """Regression: /verify-legacy must NOT trust client-supplied biometric scores.

    On the vulnerable version this test would fail with 200 + VERIFIED.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        login = await c.post(
            "/api/v1/auth/login",
            data={"username": "testuser", "password": "SecurePass123!"},
        )
        assert login.status_code == 200, login.text
        token = login.json()["access_token"]

        attack = await c.post(
            "/verify-legacy",
            json={
                "subject_id": "attacker",
                "face_score": 1.0,
                "liveness_score": 1.0,
                "antispoofing_score": 1.0,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert attack.status_code == 410, (
            f"VULNERABILITY: /verify-legacy returned {attack.status_code} "
            f"with forged scores. Body: {attack.text}"
        )
        body = attack.json()
        assert "decision" not in body
        assert "detail" in body
