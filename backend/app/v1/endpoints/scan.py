from fastapi import APIRouter, UploadFile, File
from app.services.ai_client import AIService

router = APIRouter()

@router.post("/scan")
async def scan_card(file: UploadFile = File(...)):
    contents = await file.read()
    result = AIService.scan_card(contents)
    return {"status": "success", "data": result}