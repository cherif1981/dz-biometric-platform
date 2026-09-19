from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    filename = Column(String(255))
    nin = Column(String(32), index=True)
    nom = Column(String(128))
    prenom = Column(String(128))
    raw_text = Column(Text)
    face_encoding = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())