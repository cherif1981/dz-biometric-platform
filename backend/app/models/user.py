"""User model — مع دعم RBAC."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class UserRole:
    ADMIN = "ADMIN"
    OPERATOR = "OPERATOR"
    VERIFIER = "VERIFIER"
    AUDITOR = "AUDITOR"
    ALL = [ADMIN, OPERATOR, VERIFIER, AUDITOR]


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(String, nullable=False, default=UserRole.OPERATOR, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
