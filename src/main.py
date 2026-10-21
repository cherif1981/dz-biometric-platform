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

app = FastAPI(title="dz-biometric-platform", version="1.0.0")

# --- Routeur de review (existant) ---
from src.review_api import router as review_router
app.include_router(review_router)

# --- Routeur principal de l'API v1 (AJOUT MANQUANT) ---
from src.api.v1.router import api_router
app.include_router(api_router)

# --- Moteur de décision et constructeur de rapports ---
engine = DecisionEngine("config/thresholds.yaml")
builder = ReportBuilder(engine)

if METRICS_OK:
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")


# ⚠️ L'endpoint POST /verify ci-dessous est SUPPRIMÉ pour éviter le conflit
# avec verify.router qui expose déjà POST /verify/.
# Si vous souhaitez le conserver, renommez-le en /verify-legacy.

@app.get("/health")
def health():
    return {"status": "ok", "version": app.version}