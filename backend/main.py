from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, documents, ocr, users, verification
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="DZ Biometric Platform - Algerian Identity Verification API",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(documents.router)
app.include_router(ocr.router)
app.include_router(verification.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "backend", "version": "0.1.0"}


@app.get("/")
def root():
    return {
        "message": "DZ Biometric Platform API",
        "docs": "/docs",
        "health": "/health",
    }