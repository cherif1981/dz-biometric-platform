from fastapi import APIRouter, UploadFile, File, Depends, Form
from src.core.permissions import RequireScopes
from src.modules.face_verification.detector import FaceDetector
from src.modules.face_verification.embeddings import EmbeddingExtractor
from src.modules.face_verification.matcher import FaceMatcher

router = APIRouter()
_detector = FaceDetector()
_embedder = EmbeddingExtractor()
_matcher = FaceMatcher()


@router.post("/verify")
async def verify(
    selfie: UploadFile = File(...),
    reference: UploadFile = File(...),
    _: dict = Depends(RequireScopes("write")),
):
    s = await selfie.read()
    r = await reference.read()
    fs = _detector.detect(s)
    fr = _detector.detect(r)
    es = _embedder.extract(fs)
    er = _embedder.extract(fr)
    return _matcher.compare(es, er)