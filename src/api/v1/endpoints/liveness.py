from fastapi import APIRouter, Depends, File, UploadFile

from src.core.permissions import RequireScopes
from src.modules.liveness.passive import PassiveLiveness

router = APIRouter()


@router.post("/check")
async def check(
    file: UploadFile = File(...),
    _: dict = Depends(RequireScopes("write")),
):
    data = await file.read()
    return PassiveLiveness().predict(data)
