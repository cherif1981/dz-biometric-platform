"""Verification routes — POST /api/verification/face."""
from fastapi import APIRouter, File, HTTPException, UploadFile

from app.services.face_service import FaceService

router = APIRouter()


@router.post("/face")
async def verify_face(selfie: UploadFile = File(...)):
    if not selfie.content_type or not selfie.content_type.startswith("image/"):
        raise HTTPException(400, "يجب رفع صورة صالحة")
    contents = await selfie.read()
    encoding = await FaceService.encode(contents)
    if not encoding:
        raise HTTPException(422, "لم يتم كشف وجه في الصورة")
    return {"status": "ok", "encoding": encoding}
