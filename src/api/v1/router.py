from fastapi import APIRouter

from src.api.v1.endpoints import (
    auth,
    identity,
    ocr,
    face,
    liveness,
    users,
)
from src.api.v1 import verify
from src.api.v1 import liveness as challenge_liveness
from src.api.v1 import audit as audit_stats


api_router = APIRouter()

# --- Endpoints avec préfixe défini ici (pas de préfixe interne) ---
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(identity.router, prefix="/identity", tags=["identity"])
api_router.include_router(ocr.router, prefix="/ocr", tags=["ocr"])
api_router.include_router(face.router, prefix="/face", tags=["face"])
api_router.include_router(liveness.router, prefix="/liveness", tags=["liveness"])

# --- Endpoints avec préfixe déjà défini dans leur module ---
# verify.py définit déjà APIRouter(prefix="/verify", ...) → ne pas répéter
api_router.include_router(verify.router, tags=["verification"])

# liveness.py (src/api/v1) définit déjà APIRouter(prefix="/liveness", ...)
api_router.include_router(challenge_liveness.router, tags=["liveness"])

# audit.py définit probablement déjà APIRouter(prefix="/audit", ...)
api_router.include_router(audit_stats.router, tags=["audit"])