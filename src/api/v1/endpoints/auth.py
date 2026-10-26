from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import ValidationError
from src.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from src.db.session import get_db
from src.repositories.user_repository import UserRepository

router = APIRouter()


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/login", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    repo = UserRepository(db)
    user = await repo.get_by_username(form.username)

    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    return TokenResponse(
        access_token=create_access_token(user.id, user.scopes),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(body.refresh_token)
    if payload.get("type") != "refresh":
        raise ValidationError("Not a refresh token")

    user_id = int(payload["sub"])
    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists",
        )

    return TokenResponse(
        access_token=create_access_token(user.id, user.scopes),
        refresh_token=create_refresh_token(user.id),
    )


# ===== نقطة نهاية محمية لاختبار الصلاحيات وانتهاء الرموز =====
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from src.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class UserOut(BaseModel):
    id: int
    username: str
    email: str | None = None
    scopes: list[str] = []


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Not an access token")

    repo = UserRepository(db)
    user = await repo.get_by_id(int(payload["sub"]))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@router.get("/me", response_model=UserOut)
async def read_me(current: User = Depends(get_current_user)):
    return UserOut(
        id=current.id,
        username=current.username,
        email=current.email,
        scopes=current.scopes or [],
    )
