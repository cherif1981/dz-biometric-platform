from sqlalchemy import JSON, Column, Integer, String

from src.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    password_hash = Column(String, nullable=False)
    scopes = Column(JSON, default=list)  # e.g., ["admin", "read", "write"]
