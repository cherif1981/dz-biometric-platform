import os, json, hmac, hashlib, uuid
from enum import Enum
from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import redis as redis_lib
import fakeredis
import audit

HMAC_SECRET   = os.environ.get("HMAC_SECRET", "dev-secret").encode()
REDIS_URL     = os.environ.get("REDIS_URL")
RATE_LIMIT    = os.environ.get("RATE_LIMIT", "1000/minute")
PAD_THRESHOLD = 0.5

def make_redis():
    if REDIS_URL: return redis_lib.from_url(REDIS_URL, decode_responses=True)
    return fakeredis.FakeRedis(decode_responses=True)
R = make_redis()
MODE = "redis" if REDIS_URL else "fakeredis"

limiter = Limiter(key_func=get_remote_address,
                  storage_uri=REDIS_URL or "memory://", default_limits=[])

class PADState(str, Enum):
    INITIATED="INITIATED"; CHALLENGE_ISSUED="CHALLENGE_ISSUED"
    PAD_EVALUATING="PAD_EVALUATING"; PAD_PASSED="PAD_PASSED"
    PAD_FAILED="PAD_FAILED"; MATCHING="MATCHING"
    ACCEPTED="ACCEPTED"; REJECTED="REJECTED"; TERMINATED="TERMINATED"

TRANSITIONS = {
    PADState.INITIATED:        {PADState.CHALLENGE_ISSUED, PADState.TERMINATED},
    PADState.CHALLENGE_ISSUED: {PADState.PAD_EVALUATING,   PADState.TERMINATED},
    PADState.PAD_EVALUATING:   {PADState.PAD_PASSED, PADState.PAD_FAILED, PADState.TERMINATED},
    PADState.PAD_PASSED:       {PADState.MATCHING, PADState.TERMINATED},
    PADState.MATCHING:         {PADState.ACCEPTED, PADState.REJECTED, PADState.TERMINATED},
    PADState.PAD_FAILED: set(), PADState.ACCEPTED: set(),
    PADState.REJECTED:   set(), PADState.TERMINATED: set(),
}
class StateErr(Exception): pass

def sign(p, k):
    c = json.dumps(p, sort_keys=True, separators=(",",":")).encode()
    return hmac.new(k, c, hashlib.sha256).hexdigest()

def _audit(event_type, **kw):
    try: audit.append_event(event_type, **kw)
    except Exception as e:
        raise HTTPException(500, f"audit failure: {e}")

class Session:
    def __init__(self, j, n):
        self.job_id=j; self.nonce=n; self.state=PADState.INITIATED
        self.pad_score=None; self.receipt=None
    def transition(self, new):
        if new not in TRANSITIONS.get(self.state, set()):
            raise StateErr(f"{self.state.value}->{new.value}")
        old = self.state; self.state = new; return old
    def is_terminal(self):
        return self.state in {PADState.PAD_FAILED, PADState.ACCEPTED,
                              PADState.REJECTED, PADState.TERMINATED}

def save(s):
    R.set(f"sess:{s.job_id}", json.dumps({
        "job_id":s.job_id,"nonce":s.nonce,"state":s.state.value,
        "pad_score":s.pad_score,"receipt":s.receipt}), ex=300)

def load(j):
    raw = R.get(f"sess:{j}")
    if not raw: return None
    d = json.loads(raw); s = Session(d["job_id"], d["nonce"])
    s.state=PADState(d["state"]); s.pad_score=d["pad_score"]; s.receipt=d["receipt"]
    return s

def atomic_transition(job_id, expected, new, pad_score=None, receipt=None, max_retries=3):
    """انتقال ذري: ينجح فقط إذا كانت الحالة الحالية == expected."""
    key = f"sess:{job_id}"
    for _ in range(max_retries):
        try:
            with R.pipeline() as pipe:
                pipe.watch(key)
                raw = pipe.get(key)
                if not raw:
                    pipe.unwatch(); return ("not_found", None)
                d = json.loads(raw)
                if d["state"] != expected:
                    pipe.unwatch(); return ("state_mismatch", d["state"])
                d["state"] = new
                if pad_score is not None: d["pad_score"] = pad_score
                if receipt is not None:   d["receipt"] = receipt
                pipe.multi()
                pipe.set(key, json.dumps(d), ex=300)
                pipe.execute()
                return ("ok", None)
        except redis_lib.WatchError:
            continue
    return ("conflict", None)

def run_pad(img, fail=None):
    if fail=="crash": raise RuntimeError("model crash")
    if fail=="low":   return 0.1
    return 0.95

app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

class SubmitReq(BaseModel):
    job_id: str; nonce: str; image_b64: str = ""
    failure_mode: Optional[str] = None
    # client_pad_score: حُذف — الخادم لا يقرأ درجات العميل

class RecReq(BaseModel):
    job_id: str; nonce: str; decision: str; score: float; receipt: str

@app.get("/info")
def info():
    return {"mode": MODE, "rate_limit": RATE_LIMIT,
            "storage": "redis" if REDIS_URL else "memory://"}

@app.post("/challenge")
@limiter.limit(RATE_LIMIT)
def challenge(request: Request):
    s = Session(str(uuid.uuid4()), str(uuid.uuid4()))
    s.transition(PADState.CHALLENGE_ISSUED); save(s)
    _audit("CHALLENGE_ISSUED", job_id=s.job_id, nonce=s.nonce,
           metadata={"ip": request.client.host if request.client else None})
    return {"job_id":s.job_id,"nonce":s.nonce}

@app.post("/submit")
def submit(req: SubmitReq):
    s = load(req.job_id)
    if not s:
        _audit("REJECTED", job_id=req.job_id, metadata={"reason": "unknown_job"})
        raise HTTPException(404, "unknown job")
    if not hmac.compare_digest(s.nonce, req.nonce):
        _audit("REJECTED", job_id=req.job_id, nonce=req.nonce,
               metadata={"reason": "nonce_mismatch"})
        raise HTTPException(401, "nonce")
    if s.is_terminal():
        _audit("REJECTED", job_id=req.job_id, nonce=req.nonce,
               metadata={"reason": "terminal", "state": s.state.value})
        raise HTTPException(409, f"terminal:{s.state.value}")

    # نقطة الالتزام بالتزامن: انتقال ذري (TOCTOU-safe)
    result, current = atomic_transition(
        req.job_id, PADState.CHALLENGE_ISSUED.value, PADState.PAD_EVALUATING.value)
    if result == "not_found":
        raise HTTPException(404, "unknown job")
    if result == "state_mismatch":
        _audit("REJECTED", job_id=req.job_id, nonce=req.nonce,
               metadata={"reason": "concurrent_or_unexpected", "state": current})
        raise HTTPException(409, f"state:{current}")
    if result == "conflict":
        raise HTTPException(409, "concurrent modification, retry")

    _audit("STATE_TRANSITION", job_id=req.job_id, nonce=req.nonce,
           metadata={"from": "CHALLENGE_ISSUED", "to": "PAD_EVALUATING"})

    # أعد التحميل — الحالة الآن PAD_EVALUATING
    s = load(req.job_id)

    try: score = run_pad(req.image_b64.encode(), req.failure_mode)
    except Exception as e:
        s.transition(PADState.TERMINATED); save(s)
        _audit("PAD_ERROR", job_id=s.job_id, nonce=s.nonce,
               metadata={"error": str(e)})
        raise HTTPException(503, str(e))

    s.pad_score = score
    if score < PAD_THRESHOLD:
        s.transition(PADState.PAD_FAILED); save(s)
        _audit("PAD_FAILED", job_id=s.job_id, nonce=s.nonce,
               pad_score=score, decision="REJECTED",
               metadata={"threshold": PAD_THRESHOLD})
        raise HTTPException(401, "liveness")

    # نقطة الالتزام: التدقيق أولًا، الحالة بعده
    payload = {"job_id":s.job_id,"nonce":s.nonce,"decision":"ACCEPTED","score":score}
    receipt = sign(payload, HMAC_SECRET)
    receipt_hash = hashlib.sha256(receipt.encode()).hexdigest()

    try:
        audit.append_event("ACCEPTED", job_id=s.job_id, nonce=s.nonce,
                           decision="ACCEPTED", pad_score=score,
                           receipt_hash=receipt_hash)
    except Exception as e:
        s.state = PADState.TERMINATED
        try: save(s)
        except: pass
        raise HTTPException(500, f"audit failure at commit point: {e}")

    s.transition(PADState.PAD_PASSED)
    s.transition(PADState.MATCHING)
    s.receipt = receipt
    s.transition(PADState.ACCEPTED)
    save(s)
    return {"decision": s.state.value, "receipt": s.receipt}

@app.post("/verify-receipt")
def verify_receipt(req: RecReq):
    payload = {"job_id":req.job_id,"nonce":req.nonce,"decision":req.decision,"score":req.score}
    ok = hmac.compare_digest(sign(payload, HMAC_SECRET), req.receipt)
    _audit("RECEIPT_VERIFY", job_id=req.job_id, nonce=req.nonce,
           decision=req.decision if ok else "INVALID",
           metadata={"valid": ok})
    if not ok: raise HTTPException(401, "invalid")
    return {"valid": True}
