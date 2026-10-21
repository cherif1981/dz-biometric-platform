src.api.v1.endpointfrom fastapi import APIRouter

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

# Routeurs déjà préfixés en interne ou à préfixer ici
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(identity.router, prefix="/identity", tags=["identity"])
api_router.include_router(ocr.router, prefix="/ocr", tags=["ocr"])
api_router.include_router(face.router, prefix="/face", tags=["face"])

# endpoints.liveness : on garde le préfixe /liveness ici
api_router.include_router(liveness.router, prefix="/liveness", tags=["liveness"])

# verify.py et liveness.py (src/api/v1) ont déjà leur préfixe interne :
# - verify.router  -> /verify/...
# - challenge_liveness.router -> /liveness/...
api_router.include_router(verify.router, tags=["verification"])
api_router.include_router(challenge_liveness.router, tags=["liveness"])

# audit.py a probablement déjà son préfixe interne /audit
api_router.include_router(audit_stats.router, tags=["audit"])