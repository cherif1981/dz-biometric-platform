"""User routes — POST /api/v1/users/register."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.security import hash_password
from app.models.user import UserRole
from app.repositories.user_repository import UserRepository

router = APIRouter()


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None
    role: str = UserRole.OPERATOR   # الافتراضي OPERATOR


class UserRead(BaseModel):
    id: int
    email: EmailStr
    full_name: str | None = None
    role: str

    class Config:
        from_attributes = True


@router.post("/register", response_model=UserRead)
async def register(payload: UserRegister, db: Session = Depends(get_db)):
    # ✅ تحقق من الدور
    if payload.role not in UserRole.ALL:
        raise HTTPException(400, f"دور غير صالح. الأدوار المسموحة: {UserRole.ALL}")

    # ⚠️ ملاحظة أمنية: في الإنتاج، يجب أن يكون ADMIN فقط من يستطيع
    # إنشاء ADMIN أو VERIFIER. التسجيل العام يجب أن يكون OPERATOR فقط.

    repo = UserRepository(db)
    if repo.get_by_email(payload.email):
        raise HTTPException(400, "Email déjà utilisé")

    user = repo.create(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
    )
    return user
