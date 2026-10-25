"""FastAPI entrypoint — يربط DecisionEngine و ReportBuilder و metrics."""
import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from src.core.decision_engine import DecisionEngine
from src.services.report_builder import ReportBuilder

logger = logging.getLogger(__name__)

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
from fastapi import Depends
from src.api.v1.endpoints.auth import get_current_user
from src.models.user import User
app.include_router(review_router)

# --- Routeur principal de l'API v1 (import sécurisé) ---
try:
    from src.api.v1.router import api_router
    app.include_router(api_router, prefix="/api/v1")
except ImportError as e:
    logger.warning(
        f"Impossible d'importer api_router : {e}. "
        "Certains endpoints (verify, liveness, etc.) ne seront pas disponibles. "
        "Vérifiez que opencv-python-headless est installé."
    )

# --- Moteur de décision et constructeur de rapports ---
engine = DecisionEngine("config/thresholds.yaml")
builder = ReportBuilder(engine)

# --- Métriques Prometheus ---
if METRICS_OK:
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")


class VerifyPayload(BaseModel):
    subject_id: str = "anonymous"
    face_score: float = 0.0
    liveness_score: float = 0.0
    antispoofing_score: float = 0.0


@app.post("/verify-legacy", tags=["verification-legacy"], deprecated=True, include_in_schema=False)
def verify_legacy(current: User = Depends(get_current_user)):
    """
    [DISABLED FOR SECURITY]

    The legacy contract accepted client-supplied biometric scores
    (face_score, liveness_score, antispoofing_score) and trusted them
    to issue a VERIFIED/REJECTED decision. Any authenticated user
    could forge a VERIFIED result by sending all scores as 1.0 without
    presenting any image.

    Replaced by POST /api/v1/verify/, which accepts raw id_image +
    selfie files and recomputes every score server-side.
    """
    raise HTTPException(
        status_code=410,
        detail=(
            "This endpoint has been permanently disabled for security reasons. "
            "Use POST /api/v1/verify/ with id_image and selfie files."
        ),
    )


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok", "version": app.version}


@app.get("/", tags=["root"])
def root():
    return {
        "name": "dz-biometric-platform",
        "version": app.version,
        "docs": "/docs",
        "openapi": "/openapi.json",
    }


# ===== تضمين راوتر المصادقة (auth) =====
