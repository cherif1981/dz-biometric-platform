from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Création de l'application FastAPI
app = FastAPI(
    title="dz-biometric-platform",
    version="1.0.0",
    description="Plateforme biométrique — API de vérification d'identité",
)

# Middleware CORS (à adapter selon vos besoins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routeur de review (existant) ---
from src.review_api import router as review_router
app.include_router(review_router)

# --- Routeur principal de l'API v1 (AJOUT MANQUANT) ---
from src.api.v1.router import api_router
app.include_router(api_router)


@app.get("/health", tags=["health"])
def health_check():
    """Endpoint de santé pour les sondes de disponibilité."""
    return {"status": "ok", "version": app.version}


@app.get("/", tags=["root"])
def root():
    """Racine de l'API."""
    return {
        "name": "dz-biometric-platform",
        "version": app.version,
        "docs": "/docs",
        "openapi": "/openapi.json",
    }