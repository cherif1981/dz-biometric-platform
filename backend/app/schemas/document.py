"""Pydantic schemas للوثائق — بدون حقول حساسة."""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class DocumentSafe(BaseModel):
    """عرض آمن — لا يحتوي على nin أو raw_text أو face_encoding."""
    id: int
    filename: Optional[str] = None
    nom: Optional[str] = None
    prenom: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DocumentWithNIN(DocumentSafe):
    """عرض موسّع — للـVERIFIER أو ADMIN فقط."""
    nin: Optional[str] = None
