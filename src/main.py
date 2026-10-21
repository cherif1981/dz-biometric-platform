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

from src.review_api import router as review_router
app.include_router(review_router)

from src.api.v1.verify import router as verify_router
app.include_router(verify_router, prefix="/api/v1")

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


@app.post("/verify")
def verify(payload: VerifyPayload):
    scores = {
        "face_similarity": payload.face_score,
        "liveness": payload.liveness_score,
        "antispoofing": payload.antispoofing_score,
    }
    try:
        return builder.build(payload.subject_id, scores)
    except ValueError as e:
        raise HTTPException(400, str(e))
