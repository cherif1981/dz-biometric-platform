"""OCR routes — يستقبل صورة، يعيد الحقول المستخرجة."""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from typing import Optional, Dict

from app.api.deps import require_permission
from app.services.ai_client import AIService

router = APIRouter()

MAX_FILE_SIZE = 5 * 1024 * 1024


class OCRResponse(BaseModel):
    success: bool
    confidence: Optional[float] = None
    fields: Optional[Dict] = None
    processing_time: Optional[float] = None
    error: Optional[str] = None
    # ⚠️ لا يوجد "text" — لا نُسرّب النص الخام


@router.post("/extract", response_model=OCRResponse)
async def ocr_extract(
    current_user: dict = Depends(require_permission("ocr:extract")),
    file: UploadFile = File(...),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "يجب رفع صورة صالحة")

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(413, "حجم الملف كبير جدًا (الحد 5MB)")

    try:
        result = AIService.scan_card(contents)
        if isinstance(result, dict):
            result.pop("text", None)
        return result
    except Exception as e:
        raise HTTPException(500, f"خطأ في خدمة AI: {str(e)}")
