"""KYC orchestrator — combines Path A (face) + Path B (document).

Design contract (Phase 3):
  1. Evidence from Path A and Path B NEVER modifies each other.
  2. ACCEPT requires: face.match AND document.document_authentic
     AND pad_state == VERIFIED AND policy != FORCE_REVIEW.
  3. Hard forgery evidence (MRZ detected + checksum mismatch) → REJECT,
     even under FORCE_REVIEW. Provable fraud ≠ ambiguity.
  4. All other cases → REVIEW.
  5. Any exception or missing evidence → REVIEW (fail-closed).

The orchestrator NEVER re-implements face matching, OCR, or MRZ
validation. It only combines evidence produced by independent services.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional

from anti_spoof.decision import POLICY, PADState


class KYCDecision(str, Enum):
    ACCEPT = "ACCEPT"
    REVIEW = "REVIEW"
    REJECT = "REJECT"


# ═══════════════════════════════════════════════════════════════════════
# Immutable evidence carriers
# ═══════════════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class FaceEvidence:
    similarity: float
    match: bool
    threshold: float
    error: Optional[str] = None

    @classmethod
    def from_service_result(cls, r: dict) -> "FaceEvidence":
        return cls(
            similarity=float(r.get("similarity", 0.0)),
            match=bool(r.get("match", False)),
            threshold=float(r.get("threshold", 0.0)),
        )

    @classmethod
    def failure(cls, error: str) -> "FaceEvidence":
        return cls(similarity=0.0, match=False, threshold=0.0, error=error)


@dataclass(frozen=True)
class DocumentEvidence:
    mrz_valid: bool
    document_authentic: bool
    liveness_score: float
    doc_type: str
    reasons: tuple = ()
    mrz_fields: dict = field(default_factory=dict)
    error: Optional[str] = None

    @classmethod
    def from_service_result(cls, r) -> "DocumentEvidence":
        return cls(
            mrz_valid=bool(getattr(r, "mrz_valid", False)),
            document_authentic=bool(getattr(r, "document_authentic", False)),
            liveness_score=float(getattr(r, "liveness_score", 0.0)),
            doc_type=str(getattr(r, "doc_type", "unknown")),
            reasons=tuple(getattr(r, "reasons", ()) or ()),
            mrz_fields=dict(getattr(r, "mrz_fields", {}) or {}),
        )

    @classmethod
    def failure(cls, error: str) -> "DocumentEvidence":
        return cls(mrz_valid=False, document_authentic=False,
                   liveness_score=0.0, doc_type="unknown", error=error)


@dataclass(frozen=True)
class KYCResult:
    decision: str
    reasons: tuple
    face: FaceEvidence
    document: DocumentEvidence
    pad_state: str
    policy: str

    def to_dict(self) -> dict:
        return {
            "decision": self.decision,
            "reasons": list(self.reasons),
            "face": asdict(self.face),
            "document": asdict(self.document),
            "pad_state": self.pad_state,
            "policy": self.policy,
        }


# ═══════════════════════════════════════════════════════════════════════
# Internal helpers
# ═══════════════════════════════════════════════════════════════════════
def _coerce_pad_state(state) -> PADState:
    if isinstance(state, PADState):
        return state
    if isinstance(state, str):
        try:
            return PADState(state)
        except ValueError:
            return PADState.UNAVAILABLE
    return PADState.UNAVAILABLE


def _has_hard_forgery_evidence(doc: DocumentEvidence) -> bool:
    """True only for POSITIVE, provable forgery.

    Hard = MRZ was detected and parsed, but checksums failed.
    Not hard:
      - no MRZ found (could be bad OCR)
      - document not live (could be missing detector)
      - face mismatch (could be poor selfie)
    """
    if doc.error or doc.document_authentic:
        return False
    return any("checksum_mismatch" in r for r in doc.reasons)


# ═══════════════════════════════════════════════════════════════════════
# Core orchestration (pure function, no models)
# ═══════════════════════════════════════════════════════════════════════
def orchestrate(face: FaceEvidence, document: DocumentEvidence,
                pad_state: PADState = PADState.UNAVAILABLE,
                policy: Optional[str] = None) -> KYCResult:
    """Combine independent evidence into a final decision.

    `policy` defaults to anti_spoof.decision.POLICY. Pass explicitly
    only in tests to simulate TWO_THRESHOLD.
    """
    if policy is None:
        policy = POLICY

    pad_state = _coerce_pad_state(pad_state)

    # ── Collect reasons from each path independently ──
    reasons = []
    if face.error:
        reasons.append(f"face_error:{face.error}")
    elif not face.match:
        reasons.append("face_mismatch")

    if document.error:
        reasons.append(f"document_error:{document.error}")
    else:
        reasons.extend(document.reasons)
        if not document.document_authentic and not document.reasons:
            reasons.append("document_not_authentic")

    pad_str = pad_state.value
    pol_str = str(policy)

    # ── Rule 1: hard forgery → REJECT (even under FORCE_REVIEW) ──
    if _has_hard_forgery_evidence(document):
        return KYCResult(
            decision=KYCDecision.REJECT.value,
            reasons=tuple(reasons + ["hard_forgery_evidence"]),
            face=face, document=document,
            pad_state=pad_str, policy=pol_str,
        )

    # ── Rule 2: FORCE_REVIEW blocks every ACCEPT ──
    if policy == "FORCE_REVIEW":
        return KYCResult(
            decision=KYCDecision.REVIEW.value,
            reasons=tuple(reasons + ["policy_force_review"]),
            face=face, document=document,
            pad_state=pad_str, policy=pol_str,
        )

    # ── Rule 3: only the "all green" case may ACCEPT ──
    if (face.match and document.document_authentic
            and pad_state == PADState.VERIFIED):
        return KYCResult(
            decision=KYCDecision.ACCEPT.value,
            reasons=tuple(),
            face=face, document=document,
            pad_state=pad_str, policy=pol_str,
        )

    # ── Rule 4: default ──
    return KYCResult(
        decision=KYCDecision.REVIEW.value,
        reasons=tuple(reasons),
        face=face, document=document,
        pad_state=pad_str, policy=pol_str,
    )


# ═══════════════════════════════════════════════════════════════════════
# High-level entry point (loads services lazily; catches all errors)
# ═══════════════════════════════════════════════════════════════════════
def orchestrate_from_images(
    selfie_bgr,
    document_face_bgr,
    document_image_bgr,
    pad_state: PADState = PADState.UNAVAILABLE,
    ocr_text: Optional[str] = None,
    policy: Optional[str] = None,
) -> KYCResult:
    """Extract evidence via services, then orchestrate.

    Every service call is wrapped in try/except → REVIEW on failure.
    """
    face_ev = FaceEvidence.failure("not_run")
    try:
        from src.services.face_match_service import get_face_match_service
        svc = get_face_match_service()
        face_ev = FaceEvidence.from_service_result(
            svc.match(selfie_bgr, document_face_bgr))
    except Exception as e:
        face_ev = FaceEvidence.failure(f"{type(e).__name__}: {e}")

    doc_ev = DocumentEvidence.failure("not_run")
    try:
        from src.services.document_auth_service import get_document_auth_service
        from src.services.document_ocr_service import get_document_ocr_service

        text = ocr_text
        if text is None:
            ocr = get_document_ocr_service()
            text = ocr.extract_text_string(document_image_bgr)

        auth = get_document_auth_service()
        doc_ev = DocumentEvidence.from_service_result(
            auth.validate(text, image_or_frames=document_image_bgr))
    except Exception as e:
        doc_ev = DocumentEvidence.failure(f"{type(e).__name__}: {e}")

    return orchestrate(face_ev, doc_ev, pad_state, policy=policy)
