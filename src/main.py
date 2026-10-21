"""FastAPI entrypoint — يربط DecisionEngine و ReportBuilder و metrics."""
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from src.core.decision_engine import DecisionEngine
from src.services.report_builder import ReportBuilder

try:
    from prometheus_fastapi_instrumentator import Instrumentator
    METRICS_OK = True
except ImportError:
    METRICS_OK = False


app = FastAPI(
    title="dz-biometric-platform",
    version="1.0.0",
    description="Plateforme biométrique — API de vérification d'identité",
)

# --- Routeur de review (existant) ---
from src.review_api import router as review_router
app.include_router(review_router)

# --- Routeur principal de l'API v1 (AJOUT MANQUANT) ---
from src.api.v1.router import api_router
app.include_router(api_router)

# --- Moteur de décision et constructeur de rapports ---
engine = DecisionEngine("config/thresholds.yaml")
builder = ReportBuilder(engine)

# --- Métriques Prometheus ---
if METRICS_OK:
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")


# --- Endpoint legacy renommé pour éviter le conflit avec /verify/ de verify.router ---
class VerifyPayload(BaseModel):
    subject_id: str = "anonymous"
    face_score: float = 0.0
    liveness_score: float = 0.0
    antispoofing_score: float = 0.0


@app.post("/verify-legacy", tags=["verification-legacy"])
def verify_legacy(payload: VerifyPayload):
    """
    Endpoint legacy de vérification (conservé pour compatibilité).
    Utilisez plutôt /verify/ exposé par verify.router.
    """
    scores = {
        "face_similarity": payload.face_score,
        "liveness": payload.liveness_score,
        "antispoofing": payload.antispoofing_score,
    }
    try:
        return builder.build(payload.subject_id, scores)
    except ValueError as e:
        raise HTTPException(400, str(e))


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