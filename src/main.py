from fastapi import FastAPI
from src.api.v1 import verify, liveness, audit
from src.core.upload_limits import UploadLimitMiddleware

app = FastAPI(title="DZ Biometric Platform", version="0.2.0")
app.add_middleware(UploadLimitMiddleware)
app.include_router(verify.router)
app.include_router(liveness.router)
app.include_router(audit.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "DZ Biometric Platform"}
