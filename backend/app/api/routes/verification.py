from fastapi import APIRouter, File, HTTPException, UploadFile

from app.services.verification_service import VerificationService

router = APIRouter(prefix="/api/v1/verification", tags=["verification"])


@router.post("")
async def verify_identity(
    identity_document: UploadFile = File(..., description="صورة البطاقة البيومترية"),
    selfie: UploadFile = File(..., description="صورة السيلفي"),
):
    card_data = await identity_document.read()
    selfie_data = await selfie.read()

    if not card_data or not selfie_data:
        raise HTTPException(status_code=400, detail="يجب رفع الصورتين")

    service = VerificationService()
    result = await service.full_verify(
        card_bytes=card_data,
        selfie_bytes=selfie_data,
        card_filename=identity_document.filename or "card.jpg",
        selfie_filename=selfie.filename or "selfie.jpg",
    )
    return result