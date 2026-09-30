"""DZ Biometric Platform — FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.endpoints import (
    auth,
    documents,
    ocr,
    scan,
    users,
    verification,
)
from app.core.config import settings

API_PREFIX = "/api/v1"

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Algerian Identity Verification API",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth.router,         prefix=f"{API_PREFIX}/auth",         tags=["auth"])
app.include_router(users.router,        prefix=f"{API_PREFIX}/users",        tags=["users"])
app.include_router(documents.router,    prefix=f"{API_PREFIX}/documents",    tags=["documents"])
app.include_router(verification.router, prefix=f"{API_PREFIX}/verification", tags=["verification"])
app.include_router(ocr.router,          prefix=f"{API_PREFIX}/ocr",          tags=["ocr"])
app.include_router(scan.router,         prefix=f"{API_PREFIX}/scan",         tags=["scan"])


@app.get("/health", tags=["system"])
async def health():
    return {
        "status": "ok",
        "service": "backend",
        "version": settings.app_version,
    }


@app.get("/", tags=["system"])
async def root():
    return {
        "message": settings.app_name,
        "docs": "/docs",
        "health": "/health",
        "api": API_PREFIX,
    }
