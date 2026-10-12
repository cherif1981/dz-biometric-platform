from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.v1 import verify, liveness, audit
from src.api.v1.endpoints import auth as auth_endpoints
from src.core.config import settings
from src.core.exceptions import register_exception_handlers
from src.core.upload_limits import UploadLimitMiddleware

app = FastAPI(title="DZ Biometric Platform", version="0.2.0")

# ✅ معالجات الاستثناءات الموحّدة (AppError/ValidationError/NotFoundError)
# لولا هذا السطر، تُحوَّل كل الأخطاء المخصصة إلى 500 بدلاً من 404/422.
register_exception_handlers(app)

app.add_middleware(UploadLimitMiddleware)

if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

app.include_router(
    auth_endpoints.router,
    prefix=f"{settings.API_V1_PREFIX}/auth",
    tags=["auth"],
)
app.include_router(verify.router)
app.include_router(liveness.router)
app.include_router(audit.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "DZ Biometric Platform"}
