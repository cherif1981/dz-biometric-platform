from fastapi import Depends, HTTPException, status
from src.core.security import get_current_user


class RequireScopes:
    def __init__(self, *scopes: str):
        self.scopes = set(scopes)

    async def __call__(self, user: dict = Depends(get_current_user)) -> dict:
        if not self.scopes.issubset(set(user.get("scopes", []))):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail=f"Missing scopes: {self.scopes - set(user.get('scopes', []))}",
            )
        return user