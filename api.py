"""
dz-biometric-platform — Verification API
Stage 3.2: JWT + RBAC + Rate Limiting
"""
import os, uuid, json, time
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ── Rate Limiting ──
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# ── Auth ──
from auth import (
    LoginRequest, TokenResponse, UserInfo, Role,
    authenticate_user, create_access_token,
    get_current_user, require_role, USERS_DB
)

# ── Pipeline ──
from pipeline_inline import verify_identity


# ─── إعداد FastAPI ───
app = FastAPI(
    title="DZ Biometric Platform",
    version="0.3.0-mvp-secured",
    description="Algerian ID verification API (JWT + RBAC + Rate Limit)"
)

# ─── Rate Limiter ───
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ─── تخزين مؤقت ───
RESULTS_STORE: dict = {}
START_TIME = datetime.now(timezone.utc)


# ─── نماذج الاستجابة ───
class HealthResponse(BaseModel):
    status: str
    version: str
    uptime_seconds: float
    timestamp: str


# ─── Middleware: Request ID ───
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    start = time.time()
    response = await call_next(request)
    elapsed_ms = (time.time() - start) * 1000
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Processing-Time-Ms"] = f"{elapsed_ms:.2f}"
    return response


# ═══════════════════════════════════════════════════════════
# 1. Public endpoints (بدون مصادقة)
# ═══════════════════════════════════════════════════════════

@app.get("/", tags=["public"])
async def root():
    return {
        "name": "DZ Biometric Platform",
        "version": app.version,
        "docs": "/docs",
        "endpoints": [
            "/health", "/ai/health",
            "/auth/login",
            "/verify (POST, JWT required)",
            "/verify/{id} (GET, JWT required)"
        ]
    }


@app.get("/health", response_model=HealthResponse, tags=["public"])
async def health():
    uptime = (datetime.now(timezone.utc) - START_TIME).total_seconds()
    return HealthResponse(
        status="ok",
        version=app.version,
        uptime_seconds=round(uptime, 2),
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@app.get("/ai/health", tags=["public"])
async def ai_health():
    checks = {}
    try:
        import easyocr; checks["easyocr"] = "loaded"
    except Exception as e: checks["easyocr"] = f"error: {e}"
    try:
        from insightface.app import FaceAnalysis; checks["insightface"] = "available"
    except Exception as e: checks["insightface"] = f"error: {e}"
    try:
        import mediapipe as mp; checks["mediapipe"] = "available"
    except Exception as e: checks["mediapipe"] = f"error: {e}"
    try:
        import torch
        checks["cuda"] = torch.cuda.is_available()
        if torch.cuda.is_available():
            checks["gpu"] = torch.cuda.get_device_name(0)
    except Exception:
        checks["cuda"] = False
    return {
        "status": "ok",
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# ═══════════════════════════════════════════════════════════
# 2. Auth endpoints
# ═══════════════════════════════════════════════════════════

@app.post("/auth/login", response_model=TokenResponse, tags=["auth"])
@limiter.limit("5/minute")   # منع brute-force
async def login(request: Request, body: LoginRequest):
    """تسجيل الدخول والحصول على JWT."""
    user = authenticate_user(body.username, body.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="invalid_credentials"
        )
    token, expires_in = create_access_token(user["username"], user["role"])
    return TokenResponse(
        access_token=token,
        expires_in=expires_in,
        role=user["role"]
    )


@app.get("/auth/me", response_model=UserInfo, tags=["auth"])
async def me(user: dict = Depends(get_current_user)):
    """يعرض بيانات المستخدم الحالي."""
    return UserInfo(username=user["username"], role=user["role"])


# ═══════════════════════════════════════════════════════════
# 3. Protected endpoints
# ═══════════════════════════════════════════════════════════

@app.post("/verify", tags=["verification"])
@limiter.limit("10/minute")   # rate limit للمستخدمين
async def verify(
    request: Request,
    id_card: UploadFile = File(..., description="صورة بطاقة التعريف"),
    selfie: UploadFile = File(..., description="صورة سيلفي"),
    require_liveness: bool = False,
    user: dict = Depends(require_role(Role.USER, Role.VERIFIER, Role.ADMIN))
):
    """
    endpoint التحقق — يتطلب JWT.
    الصلاحيات: user, verifier, admin.
    """
    request_id = request.state.request_id

    tmp_dir = "/tmp/dz_biometric"
    os.makedirs(tmp_dir, exist_ok=True)
    id_path = os.path.join(tmp_dir, f"{request_id}_id.jpg")
    selfie_path = os.path.join(tmp_dir, f"{request_id}_selfie.jpg")

    try:
        with open(id_path, "wb") as f:
            f.write(await id_card.read())
        with open(selfie_path, "wb") as f:
            f.write(await selfie.read())
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"file_save_error: {e}")

    try:
        result = verify_identity(
            id_path, selfie_path,
            require_liveness=require_liveness
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"pipeline_error: {e}")

    # أضف معلومات المستخدم إلى النتيجة
    result["requested_by"] = user["username"]
    result["request_id"] = request_id

    RESULTS_STORE[result["verification_id"]] = result
    return result


@app.get("/verify/{verification_id}", tags=["verification"])
async def get_verification(
    verification_id: str,
    user: dict = Depends(require_role(Role.VERIFIER, Role.ADMIN))
):
    """
    استرجاع نتيجة سابقة.
    الصلاحيات: verifier, admin فقط.
    """
    if verification_id not in RESULTS_STORE:
        raise HTTPException(status_code=404, detail="verification_not_found")
    result = RESULTS_STORE[verification_id]

    # user يمكنه رؤية نتائجه فقط
    if user["role"] == Role.USER.value:
        if result.get("requested_by") != user["username"]:
            raise HTTPException(status_code=403, detail="access_denied")

    return result


@app.get("/admin/users", tags=["admin"])
async def list_users(user: dict = Depends(require_role(Role.ADMIN))):
    """عرض المستخدمين — admin فقط."""
    return {
        "users": [
            {"username": u, "role": d["role"], "disabled": d["disabled"]}
            for u, d in USERS_DB.items()
        ]
    }
