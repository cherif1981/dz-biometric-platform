"""Reference auth flow integrating ALL security controls.

This is the pattern to follow in production. Every decision:
  1. Checks rate limit (Redis).
  2. Runs anti-spoofing (heuristic — FORCE_REVIEW).
  3. Runs OCR + verification (separate paths).
  4. Records an audit event (append-only, hash chain).
  5. Stores raw images encrypted with short TTL, then deletes.

Never assumes OCR success = document authenticity.
"""
from dataclasses import dataclass
from typing import Optional

from security.audit import AuditLog, AuditEvent
from security.ratelimit import RateLimiter, RateLimitExceeded
from security.retention import SecureStorage
from anti_spoof.decision import decide as spoof_decide, ModelStatus, Decision
from evaluation.verification.decision import (
    decide_document, ExtractionStatus, AuthenticityStatus, FinalDecision,
)
from evaluation.verification.mrz import validate_td1, all_checks_pass


@dataclass
class AuthResult:
    decision: str           # ACCEPT | REVIEW | REJECT
    reason: str
    liveness: Optional[float] = None
    extraction_ok: Optional[bool] = None
    authenticity_ok: Optional[bool] = None


class AuthFlow:
    def __init__(self, audit: AuditLog, limiter: RateLimiter,
                 storage: SecureStorage):
        self.audit = audit
        self.limiter = limiter
        self.storage = storage

    def authenticate(self, actor_id: str, session_id: str,
                     image_bytes: bytes, liveness_score: Optional[float],
                     mrz_lines: Optional[tuple], ocr_ok: bool) -> AuthResult:
        # ---- 1) Rate limit ----
        try:
            self.limiter.check(f"auth:{actor_id}")
        except RateLimitExceeded as e:
            self.audit.record(AuditEvent(
                "auth_rate_limited", actor_id, session_id, "deny",
                {"retry_after": e.retry_after},
            ))
            return AuthResult("REJECT", "rate_limited")

        # ---- 2) Anti-spoofing (heuristic) ----
        spoof_decision = spoof_decide(liveness_score, ModelStatus.HEURISTIC)
        if spoof_decision == Decision.REVIEW and liveness_score is None:
            self.audit.record(AuditEvent(
                "auth_spoof_unavailable", actor_id, session_id, "review", {}))
            return AuthResult("REVIEW", "spoof_unavailable")

        # ---- 3) Verification: MRZ authenticity (independent of OCR) ----
        auth_ok = False
        if mrz_lines and all(len(l) == 30 for l in mrz_lines):
            mrz = validate_td1(*mrz_lines)
            auth_ok = all_checks_pass(mrz)
            auth_status = (AuthenticityStatus.VERIFIED if auth_ok
                           else AuthenticityStatus.SUSPECT)
        else:
            auth_status = AuthenticityStatus.UNKNOWN

        extraction_status = ExtractionStatus.OK if ocr_ok else ExtractionStatus.FAILED
        doc_decision = decide_document(extraction_status, auth_status)

        # ---- 4) Store encrypted (temp) ----
        token = f"{session_id}.bin"
        try:
            self.storage.save(token, image_bytes)
        except Exception as e:
            self.audit.record(AuditEvent(
                "auth_storage_error", actor_id, session_id, "review",
                {"error": str(e)[:100]}))
            return AuthResult("REVIEW", "storage_error")

        # ---- 5) Audit (single event, full context) ----
        self.audit.record(AuditEvent(
            "auth_decision", actor_id, session_id, doc_decision.value.lower(),
            {
                "liveness": liveness_score,
                "spoof": spoof_decision.value,
                "ocr_ok": ocr_ok,
                "auth_ok": auth_ok,
                "mrz_present": mrz_lines is not None,
            },
        ))

        # ---- 6) Secure delete (raw image, keep only audit) ----
        self.storage.delete_now(token)

        # ---- 7) Final decision ----
        if doc_decision == FinalDecision.REJECT:
            return AuthResult("REJECT", "document_suspect",
                              liveness_score, ocr_ok, auth_ok)
        if doc_decision == FinalDecision.REVIEW:
            return AuthResult("REVIEW", "needs_human",
                              liveness_score, ocr_ok, auth_ok)
        # ACCEPT only if spoof is also OK
        if spoof_decision == Decision.ACCEPT:
            return AuthResult("ACCEPT", "all_pass",
                              liveness_score, ocr_ok, auth_ok)
        return AuthResult("REVIEW", "spoof_review",
                          liveness_score, ocr_ok, auth_ok)
