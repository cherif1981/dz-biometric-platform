from fastapi import APIRouter, UploadFile, File, Form, Depends
from src.core.permissions import RequireScopes
from src.modules.ocr.arabic_engine import ArabicEngine
from src.modules.ocr.french_engine import FrenchEngine

router = APIRouter()


@router.post("/recognize")
async def recognize(
    file: UploadFile = File(...),
    lang: str = Form("ar"),
    _: dict = Depends(RequireScopes("read")),
):
    data = await file.read()
    if lang == "ar":
        result = ArabicEngine().read(data)
    elif lang == "fr":
        result = FrenchEngine().read(data)
    else:
        result = ArabicEngine().read(data)
    return {"lang": lang, "text": result["text"], "confidence": result["confidence"]}