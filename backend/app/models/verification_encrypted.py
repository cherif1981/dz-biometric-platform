"""Verification session model — مُشفّر."""
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, LargeBinary, ForeignKey, Text
)
from sqlalchemy.sql import func
from app.core.crypto import encrypt_bytes, decrypt_bytes, encrypt_str, decrypt_str
from app.core.database import Base


class VerificationSession(Base):
    """
    جلسة تحقق — كل البيانات البيومترية مشفّرة.
    
    ⚠️ ملاحظات أمنية:
    - face_encoding و raw_text و document_image: مشفّرة بـFernet.
    - لا يوجد حقل يُخزّن هذه البيانات بدون تشفير.
    - Properties للوصول الشفّاف.
    """
    __tablename__ = "verification_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # === البيانات البيومترية (مشفّرة) ===
    _face_encoding = Column("face_encoding", LargeBinary, nullable=True)
    _raw_text = Column("raw_text", Text, nullable=True)
    _document_image = Column("document_image", LargeBinary, nullable=True)

    # === النتائج (آمنة) ===
    face_score = Column(Float, nullable=True)
    liveness_score = Column(Float, nullable=True)
    liveness_passed = Column(Boolean, nullable=True)
    ocr_confidence = Column(Float, nullable=True)
    ocr_passed = Column(Boolean, nullable=True)

    # === القرار ===
    final_decision = Column(String, nullable=True)
    decision_reasons = Column(Text, nullable=True)

    # === Metadata ===
    model_version = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)

    # === Properties ===
    @property
    def face_encoding(self):
        return decrypt_bytes(self._face_encoding)

    @face_encoding.setter
    def face_encoding(self, value):
        self._face_encoding = encrypt_bytes(value)

    @property
    def raw_text(self):
        return decrypt_str(self._raw_text)

    @raw_text.setter
    def raw_text(self, value):
        self._raw_text = encrypt_str(value)

    @property
    def document_image(self):
        return decrypt_bytes(self._document_image)

    @document_image.setter
    def document_image(self, value):
        self._document_image = encrypt_bytes(value)
