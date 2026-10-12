"""
Upload size + content validation.

SEC-07: Content-Length alone is not trustworthy. Limits enforced at:
  1. nginx: client_max_body_size (deployment)
  2. UploadLimitMiddleware: fast reject on Content-Length
  3. read_limited(): authoritative byte count while reading
  4. validate_image_bytes(): magic-byte + dimensions + integrity
"""
import io
import logging

from fastapi import HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger(__name__)

# --- Limits ---
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_REQUEST_BYTES = 25 * 1024 * 1024
MAX_IMAGE_DIMENSION = 8000
MAX_IMAGE_PIXELS = 30_000_000

ALLOWED_MIME = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
}

_MAGIC_JPEG = b"\xff\xd8\xff"
_MAGIC_PNG = b"\x89PNG\r\n\x1a\n"
_MAGIC_RIFF = b"RIFF"
_MAGIC_WEBP = b"WEBP"


def sniff_image_mime(data: bytes) -> str | None:
    """Detect MIME from magic bytes."""
    if len(data) < 12:
        return None
    if data.startswith(_MAGIC_JPEG):
        return "image/jpeg"
    if data.startswith(_MAGIC_PNG):
        return "image/png"
    if data.startswith(_MAGIC_RIFF) and data[8:12] == _MAGIC_WEBP:
        return "image/webp"
    return None


def validate_image_bytes(data: bytes, max_bytes: int = MAX_UPLOAD_BYTES) -> str:
    """Validate image payload. Returns detected MIME or raises HTTPException."""
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty image payload")
    if len(data) > max_bytes:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"Image exceeds {max_bytes} bytes",
        )
    mime = sniff_image_mime(data)
    if mime not in ALLOWED_MIME:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "Only JPEG, PNG and WebP images are accepted",
        )
    try:
        from PIL import Image
        with Image.open(io.BytesIO(data)) as im:
            w, h = im.size
            if w <= 0 or h <= 0:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST, "Invalid image dimensions"
                )
            if w > MAX_IMAGE_DIMENSION or h > MAX_IMAGE_DIMENSION:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    f"Dimensions exceed {MAX_IMAGE_DIMENSION}px per side",
                )
            if w * h > MAX_IMAGE_PIXELS:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    f"Too many pixels (max {MAX_IMAGE_PIXELS})",
                )
            im.verify()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Corrupted image: {type(e).__name__}",
        ) from None
    return mime


async def read_limited(file: UploadFile, limit: int = MAX_UPLOAD_BYTES) -> bytes:
    """Read UploadFile with hard byte limit. Does NOT trust Content-Length."""
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"File exceeds {limit} bytes",
        )
    return data


class UploadLimitMiddleware(BaseHTTPMiddleware):
    """Fast-path rejection based on Content-Length (defense in depth)."""

    def __init__(self, app, max_bytes: int = MAX_REQUEST_BYTES):
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next):
        cl = request.headers.get("content-length")
        if cl:
            try:
                size = int(cl)
            except ValueError:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Invalid Content-Length header"},
                )
            if size > self.max_bytes:
                return JSONResponse(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    content={
                        "detail": f"Request body exceeds {self.max_bytes} bytes"
                    },
                )
        return await call_next(request)
