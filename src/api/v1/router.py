from fastapi import APIRouter
from src.api.v1.endpoints import (
    auth, identity, ocr, face, liveness, users, audit,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(identity.router, prefix="/identity", tags=["identity"])
api_router.include_router(ocr.router, prefix="/ocr", tags=["ocr"])
api_router.include_router(face.router, prefix="/face", tags=["face"])
api_router.include_router(liveness.router, prefix="/liveness", tags=["liveness"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])