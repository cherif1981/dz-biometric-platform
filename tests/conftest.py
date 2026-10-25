
import os

# ⚠️ يجب ضبط المتغيرات قبل أي استيراد لـ src.*
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"
os.environ.setdefault("SECRET_KEY", "change-me-in-production-please-use-a-long-random-string")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault("REFRESH_TOKEN_EXPIRE_DAYS", "7")

import pytest
import pytest_asyncio
from sqlalchemy import select


@pytest.fixture
def client():
    """TestClient متزامن لاختبارات integration — يدعم lifespan."""
    from fastapi.testclient import TestClient
    from src.main import app
    with TestClient(app) as c:
        yield c


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _seed_db():
    from src.db.base import Base
    from src.db.session import engine, AsyncSessionLocal
    from src.models.user import User
    from src.core.security import hash_password

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as s:
        r = await s.execute(select(User).where(User.username == "testuser"))
        if not r.scalar_one_or_none():
            s.add(User(
                username="testuser",
                email="test@example.com",
                password_hash=hash_password("SecurePass123!"),
                scopes=["read", "write"],
            ))
            await s.commit()

    yield
    await engine.dispose()
