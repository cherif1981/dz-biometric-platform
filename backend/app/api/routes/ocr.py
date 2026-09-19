from fastapi import APIRouter, File, HTTPException, UploadFile

from app.services.ocr_service import OCRService

router = APIRouter(prefix="/api/ocr", tags=["ocr"])


@router.post("/extract")
async def extract(file: UploadFile = File(...)):
    data = await file.read()
    if not data:
        raise HTTPException(400, "Fichier vide")
    service = OCRService()
    return await service.process(data)