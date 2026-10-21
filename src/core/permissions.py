from fastapi import Depends, HTTPException, status
from src.core.security import get_current_user


class RequireScopes:
    def __init__(self, *scopes: str):
        self.scopes = set(scopes)

    async def __call__(self, user: dict = Depends(get_current_user)) -> dict:
        if not isinstance(user, dict):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid user context")
        raw = user.get("scopes")
        if raw is None:
            raw = []
        if not isinstance(raw, (list, tuple, set, frozenset)):
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                f"Malformed token scopes (got {type(raw).__name__})",
            )
        user_scopes = set(raw)
        missing = self.scopes - user_scopes
        if missing:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail=f"Missing scopes: {sorted(missing)}",
            )
        return user
