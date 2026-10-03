"""Document model — بيانات الوثيقة مع تشفير الحقول الحساسة."""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.core.crypto import encrypt_str, decrypt_str
from app.core.database import Base


class Document(Base):
    """وثيقة هوية — الحقول الحساسة مشفّرة."""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # حقول غير حساسة
    filename = Column(String(255))
    nom = Column(String(128))
    prenom = Column(String(128))

    # حقول حساسة (مشفّرة)
    _nin = Column("nin", Text, nullable=True)
    _raw_text = Column("raw_text", Text, nullable=True)
    _face_encoding = Column("face_encoding", Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)

    @property
    def nin(self):
        return decrypt_str(self._nin)

    @nin.setter
    def nin(self, value):
        self._nin = encrypt_str(value)

    @property
    def raw_text(self):
        return decrypt_str(self._raw_text)

    @raw_text.setter
    def raw_text(self, value):
        self._raw_text = encrypt_str(value)

    @property
    def face_encoding(self):
        return decrypt_str(self._face_encoding)

    @face_encoding.setter
    def face_encoding(self, value):
        self._face_encoding = encrypt_str(value)

    def to_safe_dict(self) -> dict:
        return {
            "id": self.id,
            "filename": self.filename,
            "nom": self.nom,
            "prenom": self.prenom,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
