from fastapi import APIRouter
from src.services.audit_db import AuditDB

router = APIRouter(prefix="/audit", tags=["audit"])
db = AuditDB()


@router.get("/stats")
def stats():
    return db.stats()


@router.get("/recent")
def recent(limit: int = 20):
    return {"records": db.recent(limit)}
