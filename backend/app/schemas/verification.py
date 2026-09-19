from datetime import datetime

from pydantic import BaseModel


class VerificationOut(BaseModel):
    id: int
    document_id: int | None = None
    match: str | None = None
    distance: float | None = None
    confidence: float | None = None
    created_at: datetime

    class Config:
        from_attributes = True