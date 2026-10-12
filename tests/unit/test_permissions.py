import pytest
from fastapi import HTTPException
from src.core.permissions import RequireScopes


@pytest.mark.asyncio
async def test_scope_ok():
    dep = RequireScopes("read")
    user = {"user_id": "1", "scopes": ["read", "write"]}
    assert await dep(user) == user


@pytest.mark.asyncio
async def test_scope_missing():
    dep = RequireScopes("admin")
    with pytest.raises(HTTPException):
        await dep({"user_id": "1", "scopes": ["read"]})