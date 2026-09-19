from datetime import datetime

from pydantic import BaseModel


class DocumentCreate(BaseModel):
    filename: str
    nin: str | None = None
    nom: str | None = None
    prenom: str | None = None
    raw_text: str | None = None


class DocumentOut(BaseModel):
    id: int
    filename: str | None = None
    nin: str | None = None
    nom: str | None = None
    prenom: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True