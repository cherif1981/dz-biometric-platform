from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.core.permissions import RequireScopes

router = APIRouter()


class UserOut(BaseModel):
    id: int
    username: str
    scopes: list[str]


@router.get("/me", response_model=UserOut)
async def me(user: dict = Depends(RequireScopes("read"))):
    return UserOut(id=int(user["user_id"]), username=f"user-{user['user_id']}", scopes=user["scopes"])