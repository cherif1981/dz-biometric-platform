from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    auth,
    documents,
    ocr,
    users,
    verification,
)
from app.core.config import settings

API_V1_PREFIX = "/api/v1"

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "DZ Biometric Platform - "
        "Algerian Identity Verification API"
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=[
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
    ],
    allow_headers=[
        "Authorization",
        "Content-Type",
    ],
)

app.include_router(
    auth.router,
    prefix=f"{API_V1_PREFIX}/auth",
)

app.include_router(
    users.router,
    prefix=f"{API_V1_PREFIX}/users",
)

app.include_router(
    documents.router,
    prefix=f"{API_V1_PREFIX}/documents",
)

app.include_router(
    ocr.router,
    prefix=f"{API_V1_PREFIX}/ocr",
)

app.include_router(
    verification.router,
    prefix=f"{API_V1_PREFIX}/verification",
)


@app.get("/health", tags=["system"])
async def health():
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
    }


@app.get("/", tags=["system"])
async def root():
    return {
        "message": settings.app_name,
        "docs": "/docs",
        "health": "/health",
        "api": API_V1_PREFIX,
    }