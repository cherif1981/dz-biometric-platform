"""Verification model — نتيجة التحقق البيومتري."""
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.core.database import Base


class Verification(Base):
    __tablename__ = "verifications"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    match = Column(String(8), nullable=True)
    distance = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)
    threshold = Column(Float, nullable=True)
    model_version = Column(String(32), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
