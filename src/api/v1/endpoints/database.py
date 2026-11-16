from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["database"])

@router.get("/health")
async def db_health():
    raise HTTPException(status_code=501, detail="Not implemented yet")
