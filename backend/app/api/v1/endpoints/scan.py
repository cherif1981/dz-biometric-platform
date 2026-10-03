"""Scan routes — مسح وثيقة الهوية."""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.deps import require_permission
from app.services.ai_client import AIService

router = APIRouter()

MAX_FILE_SIZE = 5 * 1024 * 1024


@router.post("/scan")
async def scan_card(
    current_user: dict = Depends(require_permission("scan:run")),
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
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(500, f"خطأ في خدمة AI: {str(e)}")
