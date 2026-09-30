"""Document routes — POST /api/documents/upload."""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.security import get_current_user
from app.repositories.document_repository import DocumentRepository
from app.services.document_service import DocumentService
from app.services.ocr_service import ocr_service

router = APIRouter()


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "يجب رفع صورة صالحة")

    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(400, "الملف فارغ")

    ocr_result = await ocr_service.process(contents)

    fields = ocr_result.get("fields", {}) if isinstance(ocr_result, dict) else {}
    repo = DocumentRepository(db)
    service = DocumentService(repo)
    service.create(
        filename=file.filename or "unknown",
        raw_text=ocr_result.get("raw_text") if isinstance(ocr_result, dict) else None,
        nin=fields.get("nin"),
        nom=fields.get("nom"),
        prenom=fields.get("prenom"),
    )

    return {
        "nin": fields.get("nin"),
        "nom": fields.get("nom"),
        "prenom": fields.get("prenom"),
        "date_naissance": fields.get("date_naissance"),
        "validation": ocr_result.get("validation") if isinstance(ocr_result, dict) else None,
    }
