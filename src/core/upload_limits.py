"""
Upload validation middleware — enforce max file size.
Returns JSONResponse (BaseHTTPMiddleware cannot raise HTTPException).
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

MAX_UPLOAD_MB = 5
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp", "image/bmp"}


class UploadLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "POST":
            content_length = request.headers.get("content-length")
            if content_length:
                try:
                    size = int(content_length)
                    if size > MAX_UPLOAD_BYTES:
                        logger.warning(f"Upload rejected: {size} > {MAX_UPLOAD_BYTES}")
                        return JSONResponse(
                            status_code=413,
                            content={
                                "detail": f"File too large. Max {MAX_UPLOAD_MB} MB.",
                                "max_bytes": MAX_UPLOAD_BYTES,
                                "received_bytes": size,
                            },
                        )
                except ValueError:
                    return JSONResponse(
                        status_code=400,
                        content={"detail": "Invalid Content-Length header"},
                    )
        return await call_next(request)
