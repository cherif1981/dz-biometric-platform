from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.repositories.document_repository import DocumentRepository
from app.schemas.document import DocumentOut
from app.services.ocr_service import OCRService

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentOut)
async def upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    data = await file.read()
    if not data:
        raise HTTPException(400, "Fichier vide")
    service = OCRService()
    result = await service.process(data)
    repo = DocumentRepository(db)
    doc = repo.create(
        filename=file.filename,
        nin=result["fields"].get("nin"),
        nom=result["fields"].get("nom"),
        prenom=result["fields"].get("prenom"),
        raw_text=result.get("raw_text"),
    )
    return doc