"""
Authentication & Authorization — JWT + RBAC
Using bcrypt directly (no passlib)
"""
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
from enum import Enum

import bcrypt                                    # ← بدل passlib
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel

# ─── إعدادات ───
SECRET_KEY = os.getenv("JWT_SECRET", "dev-secret-change-in-production-please")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

bearer_scheme = HTTPBearer()


# ─── دوال التشفير المباشرة ───
def hash_password(password: str) -> str:
    """تشفير كلمة المرور باستخدام bcrypt مباشرة."""
    pwd_bytes = password.encode("utf-8")[:72]    # اقصص إلى 72 بايت
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """التحقق من كلمة المرور مقابل الهاش."""
    try:
        pwd_bytes = password.encode("utf-8")[:72]
        hash_bytes = hashed.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception:
        return False


# ─── الأدوار ───
class Role(str, Enum):
    USER = "user"
    VERIFIER = "verifier"
    ADMIN = "admin"


# ─── المستخدمون ───
USERS_DB = {}

def _create_user(username: str, password: str, role: Role):
    USERS_DB[username] = {
        "username": username,
        "password_hash": hash_password(password),   # ← الدالة الجديدة
        "role": role.value,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "disabled": False
    }

_create_user("admin", "admin123", Role.ADMIN)
_create_user("verifier", "verifier123", Role.VERIFIER)
_create_user("user", "user123", Role.USER)


# ─── نماذج ───
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    role: str

class UserInfo(BaseModel):
    username: str
    role: str


# ─── دوال مساعدة ───
def authenticate_user(username: str, password: str) -> Optional[dict]:
    user = USERS_DB.get(username)
    if not user or user["disabled"]:
        return None
    if not verify_password(password, user["password_hash"]):   # ← الدالة الجديدة
        return None
    return user


def create_access_token(username: str, role: str) -> tuple[str, int]:
    expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.now(timezone.utc) + expires_delta
    payload = {
        "sub": username,
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": str(uuid.uuid4())
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token, int(expires_delta.total_seconds())


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"invalid_token: {e}",
            headers={"WWW-Authenticate": "Bearer"}
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)
) -> dict:
    payload = decode_token(credentials.credentials)
    username = payload.get("sub")
    if not username or username not in USERS_DB:
        raise HTTPException(status_code=401, detail="user_not_found")
    user = USERS_DB[username]
    if user["disabled"]:
        raise HTTPException(status_code=403, detail="user_disabled")
    return {"username": username, "role": user["role"]}


def require_role(*allowed_roles: Role):
    allowed_values = {r.value for r in allowed_roles}
    def checker(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in allowed_values:
            raise HTTPException(
                status_code=403,
                detail=f"insufficient_role: requires one of {list(allowed_values)}"
            )
        return user
    return checker
