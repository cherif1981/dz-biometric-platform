from sqlalchemy.orm import Session

from app.models.verification import Verification


class VerificationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **kwargs) -> Verification:
        v = Verification(**kwargs)
        self.db.add(v)
        self.db.commit()
        self.db.refresh(v)
        return v