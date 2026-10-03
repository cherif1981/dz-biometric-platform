import os
import logging
from io import BytesIO
from typing import Dict, List, Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, Header
from pydantic import BaseModel
from PIL import Image, UnidentifiedImageError

from ai.inference.pipeline import pipeline


# ============================================================
# Configuration
# ============================================================

SERVICE_TOKEN = os.getenv("AI_SERVICE_TOKEN")

MAX_FILE_SIZE = int(
    os.getenv("AI_MAX_FILE_SIZE", str(5 * 1024 * 1024))
)

MAX_IMAGE_PIXELS = int(
    os.getenv("AI_MAX_IMAGE_PIXELS", "25000000")
)

SERVICE_VERSION = "1.0.0"

logger = logging.getLogger("dz-biometric-ai")


# ============================================================
# FastAPI
# ============================================================

app = FastAPI(
    title="DZ Biometric AI Service",
    version=SERVICE_VERSION,
    description="خدمة OCR والتحقق من الوجه للبطاقات البيومترية الجزائرية",
)


# ============================================================
# Response Models
# ============================================================

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


# ============================================================
# Security
# ============================================================

def verify_service_token(
    authorization: Optional[str] = Header(default=None),
):
    """
    Protect internal AI endpoints.

    Expected:
        Authorization: Bearer <AI_SERVICE_TOKEN>
    """

    # Health endpoint can remain public/internal.
    if not SERVICE_TOKEN:
        # In production we should fail closed.
        logger.critical(
            "AI_SERVICE_TOKEN is not configured"
        )
        raise HTTPException(
            status_code=503,
            detail="AI service authentication is not configured",
        )

    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
        )

    scheme, _, token = authorization.partition(" ")

    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
        )

    if token != SERVICE_TOKEN:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
        )


# ============================================================
# Image Validation
# ============================================================

ALLOWED_FORMATS = {
    "JPEG",
    "PNG",
    "WEBP",
}


async def read_and_validate_image(
    file: UploadFile,
) -> bytes:

    # Do not trust Content-Type alone.
    if not file.content_type:
        raise HTTPException(
            status_code=400,
            detail="نوع الملف غير معروف",
        )

    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="يجب رفع صورة",
        )

    contents = await file.read(
        MAX_FILE_SIZE + 1
    )

    if not contents:
        raise HTTPException(
            status_code=400,
            detail="الملف فارغ",
        )

    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="حجم الصورة يتجاوز الحد المسموح",
        )

    try:
        with Image.open(BytesIO(contents)) as image:

            if image.format not in ALLOWED_FORMATS:
                raise HTTPException(
                    status_code=400,
                    detail="صيغة الصورة غير مدعومة",
                )

            width, height = image.size

            if width <= 0 or height <= 0:
                raise HTTPException(
                    status_code=400,
                    detail="أبعاد الصورة غير صالحة",
                )

            if width * height > MAX_IMAGE_PIXELS:
                raise HTTPException(
                    status_code=413,
                    detail="أبعاد الصورة كبيرة جدًا",
                )

            # Verify the actual encoded image.
            image.verify()

    except HTTPException:
        raise

    except UnidentifiedImageError:
        raise HTTPException(
            status_code=400,
            detail="الملف ليس صورة صالحة",
        )

    except Exception:
        logger.exception(
            "Image validation failed"
        )
        raise HTTPException(
            status_code=400,
            detail="تعذر التحقق من الصورة",
        )

    return contents


# ============================================================
# Health
# ============================================================

@app.get(
    "/",
    response_model=HealthResponse,
)
@app.get(
    "/internal/health",
    response_model=HealthResponse,
)
def health():

    return {
        "status": "healthy",
        "version": SERVICE_VERSION,
    }


# ============================================================
# OCR
# ============================================================

@app.post(
    "/api/v1/ocr/extract",
    response_model=OCRResponse,
)
async def ocr_extract(
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(default=None),
):

    verify_service_token(authorization)

    contents = await read_and_validate_image(file)

    try:

        return pipeline.process_card(
            contents
        )

    except Exception:

        logger.exception(
            "OCR processing failed"
        )

        # Never expose internal exception details.
        raise HTTPException(
            status_code=500,
            detail="حدث خطأ داخلي أثناء معالجة الصورة",
        )


# ============================================================
# Face Detection
# ============================================================

@app.post(
    "/api/v1/face/detect",
    response_model=FaceDetectResponse,
)
async def face_detect(
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(default=None),
):

    verify_service_token(authorization)

    contents = await read_and_validate_image(file)

    try:

        return pipeline.detect_faces(
            contents
        )

    except Exception:

        logger.exception(
            "Face detection failed"
        )

        raise HTTPException(
            status_code=500,
            detail="حدث خطأ داخلي أثناء اكتشاف الوجه",
        )


# ============================================================
# Face Verification
# ============================================================

@app.post(
    "/api/v1/face/verify",
    response_model=FaceVerifyResponse,
)
async def face_verify(
    card_image: UploadFile = File(...),
    selfie_image: UploadFile = File(...),
    authorization: Optional[str] = Header(default=None),
):

    verify_service_token(authorization)

    card_bytes = await read_and_validate_image(
        card_image
    )

    selfie_bytes = await read_and_validate_image(
        selfie_image
    )

    try:

        return pipeline.verify_faces(
            card_bytes,
            selfie_bytes,
        )

    except Exception:

        logger.exception(
            "Face verification failed"
        )

        raise HTTPException(
            status_code=500,
            detail="حدث خطأ داخلي أثناء التحقق من الوجه",
        )


# ============================================================
# Local development
# ============================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
    )