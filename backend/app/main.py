from fastapi import FastAPI
from app.api.v1.endpoints import scan

app = FastAPI(title="DZ Biometric Platform")
app.include_router(scan.router, prefix="/api/v1")