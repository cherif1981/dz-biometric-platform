"""FastAPI entrypoint — يربط DecisionEngine و ReportBuilder و metrics."""
import os
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel

from src.core.decision_engine import DecisionEngine
from src.services.report_builder import ReportBuilder

try:
    from prometheus_fastapi_instrumentator import Instrumentator
    METRICS_OK = True
except ImportError:
    METRICS_OK = False

app = FastAPI(title="dz-biometric-platform", version="1.0.0")

from src.review_api import router as review_router
app.include_router(review_router)



engine = DecisionEngine("config/thresholds.yaml")
builder = ReportBuilder(engine)

if METRICS_OK:
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")


class VerifyPayload(BaseModel):
    subject_id: str = "anonymous"
    face_score: float = 0.0
    liveness_score: float = 0.0
    antispoofing_score: float = 0.0


@app.get("/health")
def health():
    return {"status": "ok", "version": app.version}

# === P0-2.6b: mount verify router ===
from src.api.v1.verify import router as verify_router
app.include_router(verify_router)

# === P1.4: health & readiness ===
from src.api.health import router as health_router
app.include_router(health_router)
