from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.services.face_service import FaceService
from app.services.verification_service import VerificationService

router = APIRouter(prefix="/api/verification", tags=["verification"])


@router.post("/face")
async def verify_face(
    selfie: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    data = await selfie.read()
    if not data:
        raise HTTPException(400, "Fichier vide")
    face = FaceService()
    encoding = await face.encode(data)
    if not encoding:
        raise HTTPException(422, "Aucun visage détecté")
    return {"encoding": encoding}