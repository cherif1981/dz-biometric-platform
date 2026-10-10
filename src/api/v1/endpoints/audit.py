from fastapi import APIRouter, Depends, Query
from src.core.permissions import RequireScopes

router = APIRouter()


@router.get("/logs")
async def list_logs(
    limit: int = Query(50, le=500),
    _: dict = Depends(RequireScopes("admin")),
):
    # TODO: read from repository
    return {"items": [], "limit": limit}