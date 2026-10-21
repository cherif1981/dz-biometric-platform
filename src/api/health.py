import pathlib
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def health():
    from src.main import app
    return {"status": "ok", "version": app.version}

@router.get("/ready")
def ready():
    checks = {}
    db_error = None
    for driver in ("postgresql+psycopg2", "postgresql+psycopg", "sqlite"):
        try:
            from src.core.config import settings
            from sqlalchemy import create_engine, text
            base = settings.DATABASE_URL.replace("+asyncpg","").replace("+aiosqlite","")
            if driver == "sqlite":
                url = "sqlite:///./.ready_probe.db"
            elif base.startswith("postgresql"):
                url = driver + base[len("postgresql"):]
            else:
                continue
            eng = create_engine(url, pool_pre_ping=True)
            with eng.connect() as c:
                c.execute(text("SELECT 1"))
            checks["db"] = {"ok": True, "driver": driver}
            db_error = None
            break
        except Exception as e:
            db_error = f"{driver}: {type(e).__name__}: {e}"
    if "db" not in checks:
        checks["db"] = {"ok": False, "error": db_error}
    try:
        import redis
        from src.core.config import settings
        redis.Redis.from_url(settings.REDIS_URL, socket_timeout=1.0).ping()
        checks["redis"] = {"ok": True}
    except Exception as e:
        checks["redis"] = {"ok": False, "error": f"{type(e).__name__}: {e}"}
    try:
        checks["models_manifest"] = {"ok": pathlib.Path("models/manifest.json").exists()}
    except Exception as e:
        checks["models_manifest"] = {"ok": False, "error": str(e)}
    return {"ready": all(v["ok"] for v in checks.values()), "checks": checks}
