"""Verification routes — POST /api/v1/verification/face."""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.deps import require_permission
from app.services.face_service import FaceService

router = APIRouter()

MAX_FILE_SIZE = 5 * 1024 * 1024


@router.post("/face")
async def verify_face(
    current_user: dict = Depends(require_permission("verification:create")),
    selfie: UploadFile = File(...),
):
    if not selfie.content_type or not selfie.content_type.startswith("image/"):
        raise HTTPException(400, "يجب رفع صورة صالحة")

    contents = await selfie.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(413, "حجم الصورة كبير جدًا (الحد 5MB)")

    encoding = await FaceService.encode(contents)
    if not encoding:
        raise HTTPException(422, "لم يتم كشف وجه في الصورة")

    return {"status": "ok", "face_detected": True}
