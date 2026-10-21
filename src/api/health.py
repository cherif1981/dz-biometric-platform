import pathlib
"""Health & readiness endpoints."""
from fastapi import APIRouter
from loguru import logger

router = APIRouter()


@router.get("/health")
def health():
    from src.main import app
    return {"status": "ok", "version": app.version}


@router.get("/ready")
def ready():
    """Readiness: DB + Redis. لا يفشل إن لم يكونا مُهيّئين — بل يُبلّغ."""
    checks = {}

    # DB
    try:
        from src.core.config import settings
        from sqlalchemy import create_engine, text
        url = settings.DATABASE_URL.replace("+asyncpg", "").replace("+aiosqlite", "")
        eng = create_engine(url, pool_pre_ping=True)
        with eng.connect() as c:
            c.execute(text("SELECT 1"))
        checks["db"] = {"ok": True}
    except Exception as e:
        checks["db"] = {"ok": False, "error": f"{type(e).__name__}: {e}"}

    # Redis
    try:
        import redis
        from src.core.config import settings
        r = redis.Redis.from_url(settings.REDIS_URL, socket_timeout=1.0)
        r.ping()
        checks["redis"] = {"ok": True}
    except Exception as e:
        checks["redis"] = {"ok": False, "error": f"{type(e).__name__}: {e}"}

    # Models manifest
    try:
        mp = pathlib.Path("models/manifest.json")
        checks["models_manifest"] = {"ok": mp.exists()}
    except Exception as e:
        checks["models_manifest"] = {"ok": False, "error": str(e)}

    all_ok = all(v["ok"] for v in checks.values())
    return {"ready": all_ok, "checks": checks}
