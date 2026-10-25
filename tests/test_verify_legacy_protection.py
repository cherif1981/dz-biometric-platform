
import pytest
from httpx import AsyncClient, ASGITransport
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
