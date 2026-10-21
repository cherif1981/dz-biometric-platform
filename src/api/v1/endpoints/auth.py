"""Authentication endpoints — no demo bypass, safe bootstrap."""
import os

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from src.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)

router = APIRouter()


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


# ============================================================
# User store (bootstrap only)
# ============================================================
# In production, replace with a real repository (SQLAlchemy/LDAP).
#
# Bootstrap admin — set BOOTSTRAP_ADMIN_HASH (bcrypt hash of password):
#   python -c "from passlib.context import CryptContext; \
#              print(CryptContext(schemes=['bcrypt']).hash('YourPassword'))"
#
# If BOOTSTRAP_ADMIN_HASH is unset, NO users exist and ALL logins fail 401.
# There is intentionally no demo/demo bypass.
# ============================================================
_BOOTSTRAP_ADMIN_HASH = os.getenv("BOOTSTRAP_ADMIN_HASH", "").strip()


def _users_by_username() -> dict:
    if not _BOOTSTRAP_ADMIN_HASH:
        return {}
    return {
        "admin": {
            "id": 1,
            "username": "admin",
            "password_hash": _BOOTSTRAP_ADMIN_HASH,
            "scopes": [
                "admin", "read", "write",
                "review:read", "review:write", "review:decide",
            ],
            "active": True,
        }
    }


def _users_by_id() -> dict:
    return {
        str(u["id"]): u
        for u in _users_by_username().values()
        if u.get("active")
    }


def _safe_verify(plain: str, hashed: str) -> bool:
    """Bcrypt verify, tolerates malformed hashes (never raises)."""
    if not plain or not hashed:
        return False
    try:
        return verify_password(plain, hashed)
    except Exception:
        return False


@router.post("/login", response_model=TokenResponse)
async def login(form: OAuth2PasswordRequestForm = Depends()):
    user = _users_by_username().get(form.username)
    if not user or not _safe_verify(form.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(
        access_token=create_access_token(user["id"], user["scopes"]),
        refresh_token=create_refresh_token(user["id"]),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest):
    """Issue new tokens ONLY if user still exists and is active.

    Uses fresh scopes from the user store — not stale data from the token.
    """
    payload = decode_token(body.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong token type")
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token payload")

    user = _users_by_id().get(str(sub))
    if not user:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "User no longer valid — please log in again",
        )

    return TokenResponse(
        access_token=create_access_token(user["id"], user["scopes"]),
        refresh_token=create_refresh_token(user["id"]),
    )
