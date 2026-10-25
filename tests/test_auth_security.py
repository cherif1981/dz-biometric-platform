
import pytest
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient, ASGITransport
from jose import jwt
from src.main import app
from src.core.config import settings

AUTH_BASE = "/api/v1/auth"


@pytest.mark.asyncio
async def test_demo_bypass_removed():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post(f"{AUTH_BASE}/login",
                         data={"username": "demo", "password": "demo"})
    assert r.status_code == 401, f"expected 401, got {r.status_code}: {r.text}"


@pytest.mark.asyncio
async def test_valid_login_returns_tokens():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post(f"{AUTH_BASE}/login",
                         data={"username": "testuser", "password": "SecurePass123!"})
    assert r.status_code == 200, f"expected 200, got {r.status_code}: {r.text}"
    body = r.json()
    assert "access_token" in body and "refresh_token" in body
    assert body.get("token_type") == "bearer"


@pytest.mark.asyncio
async def test_me_with_valid_token():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        login = await c.post(f"{AUTH_BASE}/login",
                             data={"username": "testuser", "password": "SecurePass123!"})
        assert login.status_code == 200, login.text
        token = login.json()["access_token"]
        r = await c.get(f"{AUTH_BASE}/me",
                        headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    assert r.json()["username"] == "testuser"


@pytest.mark.asyncio
async def test_expired_token_rejected():
    expire = datetime.now(timezone.utc) - timedelta(minutes=5)
    payload = {"sub": "1", "exp": expire, "scopes": ["read"], "type": "access"}
    expired = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get(f"{AUTH_BASE}/me",
                        headers={"Authorization": f"Bearer {expired}"})
    assert r.status_code == 401, r.text


@pytest.mark.asyncio
async def test_refresh_token_rejected_as_access():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        login = await c.post(f"{AUTH_BASE}/login",
                             data={"username": "testuser", "password": "SecurePass123!"})
        assert login.status_code == 200, login.text
        refresh = login.json()["refresh_token"]
        r = await c.get(f"{AUTH_BASE}/me",
                        headers={"Authorization": f"Bearer {refresh}"})
    assert r.status_code == 401, r.text


@pytest.mark.asyncio
async def test_missing_token_rejected():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get(f"{AUTH_BASE}/me")
    assert r.status_code == 401, r.text
