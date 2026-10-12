"""
Scope-based authorization dependency.

Usage:
    router = APIRouter(
        prefix="/audit",
        dependencies=[Depends(RequireScopes("admin"))],
    )
"""
import logging

from fastapi import Depends, HTTPException, status

from src.core.security import get_current_user

logger = logging.getLogger(__name__)


def RequireScopes(*required: str):
    """
    Dependency factory. Returns a dependency that requires the
    authenticated user to hold ALL the given scopes.

    Scopes come from the "scopes" claim in the JWT (set by auth.login
    via create_access_token(..., scopes=[...])).
    """
    needed = set(required)

    async def _check(user: dict = Depends(get_current_user)) -> dict:
        user_scopes = set(user.get("scopes", []))
        missing = needed - user_scopes
        if missing:
            logger.info(
                "Access denied: user=%s missing scopes=%s",
                user.get("user_id"),
                sorted(missing),
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return _check
