from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from src.services.challenge_liveness import ChallengeResponseLiveness
from src.core.security import get_current_user

router = APIRouter(
    prefix="/liveness",
    tags=["liveness"],
    dependencies=[Depends(get_current_user)],
)
engine = ChallengeResponseLiveness(actions_per_challenge=2)


class F(BaseModel):
    yaw: float = 0.0
    pitch: float = 0.0
    ear: float = 0.3
    mouth_ratio: float = 0.0
    pitch_history: list = []


@router.post("/challenge/new")
def new_challenge():
    c = engine.new_challenge()
    return {
        "session_id": c.session_id,
        "actions": c.actions,
        "expires_in": engine.SESSION_TTL,
        "instructions": {
            "blink": "ارمش",
            "turn_left": "أدر يساراً",
            "turn_right": "أدر يميناً",
            "smile": "ابتسم",
            "nod": "حرّك رأسك",
        },
    }


@router.post("/challenge/{sid}/frame")
def frame(sid: str, f: F):
    r = engine.process_frame(sid, f.dict())
    return {
        "passed": r.passed,
        "completed": r.completed,
        "missing": r.missing,
        "confidence": r.confidence,
        "reason": r.reason,
    }


@router.get("/challenge/{sid}")
def get(sid: str):
    s = engine.get_session(sid)
    if not s:
        raise HTTPException(404, "not found")
    return {
        "session_id": s.session_id,
        "actions": s.actions,
        "completed": s.completed,
        "frames_analyzed": s.frames_analyzed,
    }
