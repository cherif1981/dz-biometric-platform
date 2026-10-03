"""Security — JWT، تشفير كلمات المرور، المصادقة."""
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ============================================================
# Password hashing — bcrypt مباشرة (بدون passlib)
# ============================================================
BCRYPT_MAX_BYTES = 72


def _truncate_password(password: str) -> bytes:
    """bcrypt يقبل فقط 72 بايت كحد أقصى."""
    pwd_bytes = password.encode("utf-8")
    return pwd_bytes[:BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    """يُرجع hash كـstring."""
    pwd = _truncate_password(password)
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """يتحقق من كلمة المرور."""
    try:
        pwd = _truncate_password(plain)
        return bcrypt.checkpw(pwd, hashed.encode("utf-8"))
    except Exception:
        return False


# ============================================================
# JWT
# ============================================================
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


# ============================================================
# get_current_user — يعيد dict مع sub + role
# ============================================================
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="بيانات الاعتماد غير صالحة",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    from app.repositories.user_repository import UserRepository
    repo = UserRepository(db)
    user = repo.get_by_email(email)
    if user is None:
        raise credentials_exception

    return {
        "sub": user.email,
        "user_id": user.id,
        "role": getattr(user, "role", "OPERATOR"),
    }
