"""Database — SQLAlchemy engine + session + get_db dependency."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency لإرجاع جلسة DB لكل request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
