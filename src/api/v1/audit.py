from fastapi import APIRouter, Depends

from src.core.permissions import RequireScopes
from src.services.audit_db import AuditDB

router = APIRouter(
    prefix="/audit",
    tags=["audit"],
    dependencies=[Depends(RequireScopes("admin"))],
)

db = AuditDB()


@router.get("/stats")
def stats():
    return db.stats()


@router.get("/recent")
def recent(limit: int = 10):
    return {"records": db.recent(limit=limit)}
