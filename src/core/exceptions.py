from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from loguru import logger


class AppError(Exception):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "app_error"

    def __init__(self, message: str, details: dict | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class ValidationError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "validation_error"


class BiometricError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "biometric_error"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error_handler(request: Request, exc: AppError):
        logger.warning(f"{exc.code}: {exc.message}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.code, "message": exc.message, "details": exc.details},
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        logger.exception("Unhandled error")
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error", "message": "Internal server error"},
        )