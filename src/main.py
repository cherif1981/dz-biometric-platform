from fastapi import FastAPI, Depends, Request, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import structlog, time, uuid
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from src.api.v1 import verify, liveness, audit
from src.api.v1.endpoints import auth, users
from src.core.upload_limits import UploadLimitMiddleware
from src.core.security import get_current_user
from src.core.config import settings

# ── Rate limiter (global 200/min per IP) ────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

app = FastAPI(title="DZ Biometric Platform", version="0.3.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ── CORS: ONLY explicit origins (no wildcard) ───────────────
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8080",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8080",
    # أضف نطاقات الإنتاج هنا لاحقاً
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)

# ── Existing upload size middleware ─────────────────────────
app.add_middleware(UploadLimitMiddleware)

# ── PUBLIC routes ───────────────────────────────────────────
app.include_router(auth.router)      # /auth/login must stay public
app.include_router(users.router)     # individual endpoints handle own auth

# ── PROTECTED routes (router-level dependency) ──────────────
app.include_router(verify.router,    dependencies=[Depends(get_current_user)])
app.include_router(liveness.router,  dependencies=[Depends(get_current_user)])
app.include_router(audit.router,     dependencies=[Depends(get_current_user)])

@app.get("/health")
def health():
    return {"status": "ok", "service": "DZ Biometric Platform"}


@app.middleware("http")
async def _obs_middleware(request: Request, call_next):
    start = time.perf_counter()
    try:
        response = await call_next(request)
        status = response.status_code
    except Exception:
        status = 500
        raise
    finally:
        dur = time.perf_counter() - start
        path = request.url.path
        REQ_COUNT.labels(method=request.method, path=path, status=status).inc()
        REQ_LAT.labels(path=path).observe(dur)
        logger.info("http_request", method=request.method, path=path,
                    status=status, duration_ms=round(dur*1000, 2),
                    request_id=request.headers.get("x-request-id", str(uuid.uuid4())))
    return response


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
