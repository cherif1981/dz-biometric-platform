from fastapi import APIRouter, Depends, UploadFile, File, Form
from pydantic import BaseModel

from src.core.permissions import RequireScopes
from src.modules.document_reader.card_detector import CardDetector
from src.modules.document_reader.image_quality import check_quality
from src.modules.ocr.field_extractor import extract_fields

router = APIRouter()


class IdentityExtractResponse(BaseModel):
    document_type: str
    fields: dict
    confidence: float
    warnings: list[str] = []


@router.post("/extract", response_model=IdentityExtractResponse)
async def extract_identity(
    file: UploadFile = File(...),
    document_hint: str = Form("auto"),
    _: dict = Depends(RequireScopes("write")),
):
    image_bytes = await file.read()

    quality = check_quality(image_bytes)
    if not quality["ok"]:
        return IdentityExtractResponse(
            document_type=document_hint,
            fields={},
            confidence=0.0,
            warnings=[f"low_quality:{k}" for k in quality["issues"]],
        )

    card = CardDetector().detect(image_bytes)
    doc_type = document_hint if document_hint != "auto" else card.get("type", "unknown")
    fields, conf = extract_fields(card["image"], doc_type)

    return IdentityExtractResponse(
        document_type=doc_type, fields=fields, confidence=conf,
    )