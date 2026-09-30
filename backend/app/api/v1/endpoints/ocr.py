"""OCR routes — يستقبل صورة، يعيد النص والحقول المستخرجة."""
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict

from app.services.ai_client import AIService

router = APIRouter()


class OCRResponse(BaseModel):
    success: bool
    text: Optional[str] = None
    confidence: Optional[float] = None
    fields: Optional[Dict] = None
    processing_time: Optional[float] = None
    error: Optional[str] = None


@router.post("/extract", response_model=OCRResponse)
async def ocr_extract(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "يجب رفع صورة صالحة")
    try:
        contents = await file.read()
        return AIService.scan_card(contents)
    except Exception as e:
        raise HTTPException(500, f"خطأ في خدمة AI: {str(e)}")
