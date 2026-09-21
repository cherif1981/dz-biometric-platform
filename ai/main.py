from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional

from ai.inference.pipeline import pipeline

app = FastAPI(
    title="DZ Biometric AI Service",
    version="1.0.0",
    description="خدمة OCR والتحقق من الوجه للبطاقات البيومترية الجزائرية"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

class HealthResponse(BaseModel):
    status: str
    version: str

class OCRResponse(BaseModel):
    success: bool
    text: Optional[str] = None
    confidence: Optional[float] = None
    fields: Optional[Dict] = None
    validation: Optional[Dict] = None
    processing_time: Optional[float] = None
    error: Optional[str] = None

class FaceDetectResponse(BaseModel):
    count: int
    locations: List[List[int]]
    processing_time: float

class FaceVerifyResponse(BaseModel):
    success: bool
    verified: bool
    similarity: float
    distance: float
    message: str
    processing_time: Optional[float] = None

@app.get("/", response_model=HealthResponse)
def health():
    return {"status": "healthy", "version": "1.0.0"}

@app.post("/api/v1/ocr/extract", response_model=OCRResponse)
async def ocr_extract(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "يجب رفع صورة صالحة")
    try:
        contents = await file.read()
        return pipeline.process_card(contents)
    except Exception as e:
        raise HTTPException(500, f"خطأ: {str(e)}")

@app.post("/api/v1/face/detect", response_model=FaceDetectResponse)
async def face_detect(file: UploadFile = File(...)):
    contents = await file.read()
    return pipeline.detect_faces(contents)

@app.post("/api/v1/face/verify", response_model=FaceVerifyResponse)
async def face_verify(
    card_image: UploadFile = File(...),
    selfie_image: UploadFile = File(...)
):
    img1 = await card_image.read()
    img2 = await selfie_image.read()
    return pipeline.verify_faces(img1, img2)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
