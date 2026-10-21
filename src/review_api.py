"""مسارات المراجعة البشرية — ترتبط بـ DecisionEngine عبر final_status=REVIEW."""
from fastapi import APIRouter, HTTPException, Depends, Request
from src.core.permissions import RequireScopes
from src.core.rate_limit import limiter
from pydantic import BaseModel
from typing import List
from datetime import datetime, timezone
import uuid

router = APIRouter(prefix="/review", tags=["human-review"])
_reviews: dict = {}


class ReviewItem(BaseModel):
    decision_id: str
    scores: dict
    reasons: List[str] = []


class ReviewDecision(BaseModel):
    human_status: str   # VERIFIED | REJECTED
    reviewer_id: str
    notes: str = ""


@router.get("/pending")
def pending(user: dict = Depends(RequireScopes("review:read"))):
    return [v for v in _reviews.values() if v["human_status"] is None]


@router.post("/submit")
@limiter.limit("30/minute")
def submit(request: Request, item: ReviewItem, user: dict = Depends(RequireScopes("review:write"))):
    rid = str(uuid.uuid4())
    _reviews[rid] = {
        "id": rid,
        **item.model_dump(),
        "human_status": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return {"review_id": rid, "review": _reviews[rid]}


@router.post("/{review_id}/decide")
def decide(review_id: str, decision: ReviewDecision, user: dict = Depends(RequireScopes("review:decide"))):
    if review_id not in _reviews:
        raise HTTPException(404, "review_id not found")
    if decision.human_status not in ("VERIFIED", "REJECTED"):
        raise HTTPException(400, "human_status must be VERIFIED or REJECTED")
    _reviews[review_id].update({
        "human_status": decision.human_status,
        "reviewer_id": decision.reviewer_id,
        "notes": decision.notes,
        "decided_at": datetime.now(timezone.utc).isoformat(),
    })
    return _reviews[review_id]
