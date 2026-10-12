"""
Authentication endpoints.

Users come from APP_USERS environment variable (JSON).
Until a real user repository is wired in, this is the ONLY
supported source of credentials. No demo bypass, no hardcoded hashes.

Format:
    APP_USERS='{"admin": {"id": 1, "password_hash": "<bcrypt>", "scopes": ["admin","read","write"]}}'
"""
import json
import os
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from src.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from src.core.exceptions import ValidationError

router = APIRouter()


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


@lru_cache(maxsize=1)
def _load_users() -> dict:
    raw = os.getenv("APP_USERS", "").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"APP_USERS is not valid JSON: {e}") from e
    if not isinstance(data, dict):
        raise RuntimeError("APP_USERS must be a JSON object")
    return data


def _find_user_by_id(user_id: str | int) -> dict | None:
    for u in _load_users().values():
        if str(u.get("id")) == str(user_id):
            return u
    return None


@router.post("/login", response_model=TokenResponse)
async def login(form: OAuth2PasswordRequestForm = Depends()):
    users = _load_users()
    if not users:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured",
        )

    user = users.get(form.username)
    if not user or not verify_password(form.password, user.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenResponse(
        access_token=create_access_token(user["id"], user.get("scopes", [])),
        refresh_token=create_refresh_token(user["id"]),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest):
    payload = decode_token(body.refresh_token)
    if payload.get("type") != "refresh":
        raise ValidationError("Not a refresh token")

    user_id = payload["sub"]
    user = _find_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    return TokenResponse(
        access_token=create_access_token(user["id"], user.get("scopes", [])),
        refresh_token=create_refresh_token(user["id"]),
    )
