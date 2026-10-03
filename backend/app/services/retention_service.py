"""Retention service — حذف البيانات منتهية الصلاحية."""
import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.document import Document
from app.models.verification import Verification

logger = logging.getLogger(__name__)


class RetentionService:
    def __init__(self, db: Session):
        self.db = db

    def cleanup_expired_documents(self) -> int:
        cutoff = datetime.utcnow() - timedelta(days=settings.document_retention_days)
        deleted = (
            self.db.query(Document)
            .filter(Document.created_at < cutoff)
            .delete(synchronize_session=False)
        )
        self.db.commit()
        if deleted > 0:
            logger.info(f"Retention: حُذفت {deleted} وثيقة")
        return deleted

    def cleanup_expired_verifications(self) -> int:
        cutoff = datetime.utcnow() - timedelta(days=settings.verification_retention_days)
        deleted = (
            self.db.query(Verification)
            .filter(Verification.created_at < cutoff)
            .delete(synchronize_session=False)
        )
        self.db.commit()
        if deleted > 0:
            logger.info(f"Retention: حُذفت {deleted} تحقق")
        return deleted

    def run_all(self) -> dict:
        return {
            "documents_deleted": self.cleanup_expired_documents(),
            "verifications_deleted": self.cleanup_expired_verifications(),
        }
