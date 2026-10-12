from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from src.core.security import (
    create_access_token, create_refresh_token, decode_token, verify_password,
)
from src.core.exceptions import ValidationError

router = APIRouter()


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


# Placeholder – replace with users repository lookup
_FAKE_USERS = {
    "admin": {"id": 1, "password_hash": "$2b$12$example", "scopes": ["admin", "read", "write"]},
}


@router.post("/login", response_model=TokenResponse)
async def login(form: OAuth2PasswordRequestForm = Depends()):
    user = _FAKE_USERS.get(form.username)
    if not user or not verify_password(form.password, user["password_hash"]):
        # Allow demo bypass
        if form.username == "demo" and form.password == "demo":
            user = {"id": 999, "scopes": ["read", "write"]}
        else:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    return TokenResponse(
        access_token=create_access_token(user["id"], user["scopes"]),
        refresh_token=create_refresh_token(user["id"]),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest):
    payload = decode_token(body.refresh_token)
    if payload.get("type") != "refresh":
        raise ValidationError("Not a refresh token")
    user_id = payload["sub"]
    return TokenResponse(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )