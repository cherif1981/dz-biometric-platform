"""SEC-05: RequireScopes enforcement."""
import pytest
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_requires_all_scopes():
    from src.core.permissions import RequireScopes

    check = RequireScopes("admin", "read")

    # mock user with both scopes
    user = {"user_id": "1", "scopes": ["admin", "read", "write"]}
    result = await check(user=user)
    assert result == user


@pytest.mark.asyncio
async def test_missing_scope_raises_403():
    from src.core.permissions import RequireScopes

    check = RequireScopes("admin")
    user = {"user_id": "1", "scopes": ["read", "write"]}

    with pytest.raises(HTTPException) as ei:
        await check(user=user)
    assert ei.value.status_code == 403
