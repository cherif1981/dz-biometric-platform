"""Async SQLAlchemy engine + Base. Reads DATABASE_URL from env."""
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

_RAW = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./biometric.db")
if _RAW.startswith("postgresql://"):
    _RAW = _RAW.replace("postgresql://", "postgresql+asyncpg://", 1)

DATABASE_URL = _RAW
engine = create_async_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with SessionLocal() as s:
        yield s

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
