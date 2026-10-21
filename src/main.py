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

engine = DecisionEngine("config/thresholds.yaml")
builder = ReportBuilder(engine)

if METRICS_OK:
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")


class VerifyPayload(BaseModel):
    subject_id: str = "anonymous"
    face_score: float = 0.0
    liveness_score: float = 0.0
    antispoofing_score: float = 0.0



# === P0-2.6b: mount verify router ===
from src.api.v1.verify import router as verify_router

# === P1.4: health & readiness ===
from src.api.health import router as health_router
app.include_router(health_router)

# ============================================================
# P1.7-P1.9: logging + rate limiting + API versioning
# ============================================================
from src.core.logging_setup import setup_logging
setup_logging()

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from src.core.rate_limit import limiter

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Canonical: /api/v1/...
app.include_router(verify_router, prefix="/api/v1")
app.include_router(review_router, prefix="/api/v1")

# Legacy aliases (deprecated, not in schema) — remove in v2
app.include_router(verify_router, include_in_schema=False, deprecated=True)
app.include_router(review_router, include_in_schema=False, deprecated=True)

# Optional: mount full v1 api_router (auth/users/identity/...) if importable
try:
    from src.api.v1.router import api_router as _v1_router
    app.include_router(_v1_router, prefix="/api/v1")
    print("[main] api_router mounted at /api/v1")
except Exception as _e:  # pragma: no cover
    print(f"[main] api_router NOT mounted: {type(_e).__name__}: {_e}")

