from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.security import hash_password
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserOut

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("/register", response_model=UserOut)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    if repo.get_by_email(payload.email):
        raise HTTPException(400, "Email déjà utilisé")
    user = repo.create(
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    return user


@router.get("/me", response_model=UserOut)
def me(db: Session = Depends(get_db)):
    # Simplified: replace with real auth dependency
    raise HTTPException(501, "Not implemented")