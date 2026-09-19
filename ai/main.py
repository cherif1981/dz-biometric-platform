from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from detection.card_detector import CardDetector
from face.face_detector import FaceDetector
from face.face_embedding import FaceEmbedder
from face.face_verification import verify_faces
from ocr.ocr_engine import OCREngine
from ocr.parser import parse_fields
from preprocessing import (
    correct_perspective,
    denoise_image,
    enhance_contrast,
    resize_image,
)
from validation.document_validator import validate_document

app = FastAPI(title="DZ Biometric AI Service", version="0.1.0")

detector = CardDetector()
ocr = OCREngine()
face_det = FaceDetector()
face_emb = FaceEmbedder()


class FaceCompareRequest(BaseModel):
    encoding1: list[float]
    encoding2: list[float]


@app.get("/health")
def health():
    return {"status": "ok", "service": "ai"}


@app.post("/process")
async def process(file: UploadFile = File(...)):
    import cv2
    import numpy as np

    data = await file.read()
    arr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(400, "Image invalide")

    img = resize_image(img)
    img = denoise_image(img)
    img = enhance_contrast(img)

    corners = detector.detect(img)
    if corners is not None:
        img = correct_perspective(img, corners)

    text = ocr.extract_text(img)
    fields = parse_fields(text)
    validation = validate_document(fields)

    locations = face_det.detect(img)
    face_encoding = None
    if locations:
        face_encoding = face_emb.embed(img, locations[0])

    return {
        "fields": fields,
        "validation": validation,
        "raw_text": text,
        "face_encoding": face_encoding,
    }


@app.post("/face/compare")
def face_compare(req: FaceCompareRequest):
    return verify_faces(req.encoding1, req.encoding2)