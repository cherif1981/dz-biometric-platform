"""KYC orchestrator tests — evidence independence + FORCE_REVIEW invariant."""
import pytest
from anti_spoof.decision import POLICY, PADState
from src.services.kyc_orchestrator import (
    FaceEvidence, DocumentEvidence, KYCResult, KYCDecision,
    orchestrate, _has_hard_forgery_evidence, _coerce_pad_state,
)


# ═══ Dataclass round-trips ═══════════════════════════════════════════
class TestEvidenceDataclasses:
    def test_face_evidence_from_service_result(self):
        e = FaceEvidence.from_service_result(
            {"similarity": 0.87, "match": True, "threshold": 0.35})
        assert e.similarity == 0.87
        assert e.match is True
        assert e.threshold == 0.35
        assert e.error is None

    def test_face_evidence_failure(self):
        e = FaceEvidence.failure("no face detected")
        assert e.match is False
        assert e.similarity == 0.0
        assert e.error == "no face detected"

    def test_document_evidence_from_result_object(self):
        class FakeResult:
            mrz_valid = True
            document_authentic = True
            liveness_score = 0.95
            doc_type = "passport"
            reasons = ()
            mrz_fields = {"document_number": "L898902C3"}
        e = DocumentEvidence.from_service_result(FakeResult())
        assert e.mrz_valid is True
        assert e.document_authentic is True
        assert e.liveness_score == 0.95
        assert e.mrz_fields["document_number"] == "L898902C3"

    def test_document_evidence_failure(self):
        e = DocumentEvidence.failure("ocr failed")
        assert e.mrz_valid is False
        assert e.error == "ocr failed"

    def test_kyc_result_to_dict(self):
        face = FaceEvidence(similarity=0.9, match=True, threshold=0.35)
        doc = DocumentEvidence(
            mrz_valid=True, document_authentic=True,
            liveness_score=0.95, doc_type="passport")
        r = orchestrate(face, doc, PADState.VERIFIED, policy="TWO_THRESHOLD")
        d = r.to_dict()
        assert d["decision"] == "ACCEPT"
        assert d["face"]["match"] is True
        assert d["document"]["mrz_valid"] is True


# ═══ Helpers ═════════════════════════════════════════════════════════
class TestHelpers:
    def test_coerce_pad_state_from_enum(self):
        assert _coerce_pad_state(PADState.VERIFIED) == PADState.VERIFIED

    def test_coerce_pad_state_from_string(self):
        assert _coerce_pad_state("VERIFIED") == PADState.VERIFIED

    def test_coerce_pad_state_invalid_string(self):
        assert _coerce_pad_state("garbage") == PADState.UNAVAILABLE

    def test_coerce_pad_state_none(self):
        assert _coerce_pad_state(None) == PADState.UNAVAILABLE

    def test_hard_forgery_true_on_checksum_mismatch(self):
        doc = DocumentEvidence(
            mrz_valid=False, document_authentic=False,
            liveness_score=0.95, doc_type="passport",
            reasons=("doc_no_checksum_mismatch",))
        assert _has_hard_forgery_evidence(doc) is True

    def test_hard_forgery_false_when_authentic(self):
        doc = DocumentEvidence(
            mrz_valid=True, document_authentic=True,
            liveness_score=0.95, doc_type="passport")
        assert _has_hard_forgery_evidence(doc) is False

    def test_hard_forgery_false_on_no_mrz(self):
        doc = DocumentEvidence(
            mrz_valid=False, document_authentic=False,
            liveness_score=0.95, doc_type="unknown",
            reasons=("no_mrz_found",))
        assert _has_hard_forgery_evidence(doc) is False


# ═══ Policy enforcement ══════════════════════════════════════════════
class TestPolicyEnforcement:
    def _green(self):
        return (
            FaceEvidence(similarity=0.9, match=True, threshold=0.35),
            DocumentEvidence(
                mrz_valid=True, document_authentic=True,
                liveness_score=0.95, doc_type="passport"),
        )

    def test_force_review_blocks_accept_on_green(self):
        face, doc = self._green()
        r = orchestrate(face, doc, PADState.VERIFIED, policy="FORCE_REVIEW")
        assert r.decision == KYCDecision.REVIEW.value
        assert "policy_force_review" in r.reasons

    def test_two_threshold_accepts_green(self):
        face, doc = self._green()
        r = orchestrate(face, doc, PADState.VERIFIED, policy="TWO_THRESHOLD")
        assert r.decision == KYCDecision.ACCEPT.value

    def test_two_threshold_reviews_face_mismatch(self):
        face = FaceEvidence(similarity=0.1, match=False, threshold=0.35)
        _, doc = self._green()
        r = orchestrate(face, doc, PADState.VERIFIED, policy="TWO_THRESHOLD")
        assert r.decision == KYCDecision.REVIEW.value
        assert "face_mismatch" in r.reasons

    def test_two_threshold_reviews_not_authentic_doc(self):
        face, _ = self._green()
        doc = DocumentEvidence(
            mrz_valid=False, document_authentic=False,
            liveness_score=0.1, doc_type="passport",
            reasons=("document_not_live",))
        r = orchestrate(face, doc, PADState.VERIFIED, policy="TWO_THRESHOLD")
        assert r.decision == KYCDecision.REVIEW.value
        assert "document_not_live" in r.reasons

    def test_two_threshold_reviews_heuristic_pad(self):
        face, doc = self._green()
        r = orchestrate(face, doc, PADState.HEURISTIC, policy="TWO_THRESHOLD")
        assert r.decision == KYCDecision.REVIEW.value

    def test_two_threshold_reviews_unavailable_pad(self):
        face, doc = self._green()
        r = orchestrate(face, doc, PADState.UNAVAILABLE, policy="TWO_THRESHOLD")
        assert r.decision == KYCDecision.REVIEW.value


# ═══ Hard forgery → REJECT even under FORCE_REVIEW ═══════════════════
class TestHardForgery:
    def test_checksum_mismatch_rejects_under_force_review(self):
        face = FaceEvidence(similarity=0.9, match=True, threshold=0.35)
        doc = DocumentEvidence(
            mrz_valid=False, document_authentic=False,
            liveness_score=0.95, doc_type="passport",
            reasons=("doc_no_checksum_mismatch",))
        r = orchestrate(face, doc, PADState.VERIFIED, policy="FORCE_REVIEW")
        assert r.decision == KYCDecision.REJECT.value
        assert "hard_forgery_evidence" in r.reasons

    def test_no_mrz_stays_review_under_force_review(self):
        face = FaceEvidence(similarity=0.9, match=True, threshold=0.35)
        doc = DocumentEvidence(
            mrz_valid=False, document_authentic=False,
            liveness_score=0.95, doc_type="unknown",
            reasons=("no_mrz_found",))
        r = orchestrate(face, doc, PADState.VERIFIED, policy="FORCE_REVIEW")
        assert r.decision == KYCDecision.REVIEW.value  # not REJECT

    def test_not_live_stays_review_under_force_review(self):
        face = FaceEvidence(similarity=0.9, match=True, threshold=0.35)
        doc = DocumentEvidence(
            mrz_valid=True, document_authentic=False,
            liveness_score=0.1, doc_type="passport",
            reasons=("document_not_live",))
        r = orchestrate(face, doc, PADState.VERIFIED, policy="FORCE_REVIEW")
        assert r.decision == KYCDecision.REVIEW.value  # not REJECT


# ═══ Evidence independence ═══════════════════════════════════════════
class TestEvidenceIndependence:
    def test_face_and_doc_evidence_preserved_verbatim(self):
        face = FaceEvidence(similarity=0.42, match=False, threshold=0.35)
        doc = DocumentEvidence(
            mrz_valid=True, document_authentic=True,
            liveness_score=0.88, doc_type="passport",
            reasons=(), mrz_fields={"document_number": "X123"})
        r = orchestrate(face, doc, PADState.VERIFIED)
        assert r.face == face
        assert r.document == doc

    def test_face_failure_does_not_modify_doc(self):
        face = FaceEvidence.failure("model crashed")
        doc = DocumentEvidence(
            mrz_valid=True, document_authentic=True,
            liveness_score=0.95, doc_type="passport")
        r = orchestrate(face, doc, PADState.VERIFIED)
        assert r.face.error == "model crashed"
        assert r.document.mrz_valid is True  # untouched
        assert r.document.document_authentic is True

    def test_doc_failure_does_not_modify_face(self):
        face = FaceEvidence(similarity=0.9, match=True, threshold=0.35)
        doc = DocumentEvidence.failure("ocr crashed")
        r = orchestrate(face, doc, PADState.VERIFIED)
        assert r.document.error == "ocr crashed"
        assert r.face.match is True  # untouched


# ═══ Fail-closed defaults ════════════════════════════════════════════
class TestFailClosed:
    def test_both_errors_returns_review(self):
        face = FaceEvidence.failure("a")
        doc = DocumentEvidence.failure("b")
        r = orchestrate(face, doc)
        assert r.decision == KYCDecision.REVIEW.value

    def test_default_pad_state_is_unavailable(self):
        face = FaceEvidence(similarity=0.9, match=True, threshold=0.35)
        doc = DocumentEvidence(
            mrz_valid=True, document_authentic=True,
            liveness_score=0.95, doc_type="passport")
        r = orchestrate(face, doc)  # no pad_state
        assert r.pad_state == PADState.UNAVAILABLE.value
        assert r.decision == KYCDecision.REVIEW.value


# ═══ Phase 1 invariant preserved ═════════════════════════════════════
class TestPhase1InvariantPreserved:
    def test_current_policy_is_force_review(self):
        assert POLICY == "FORCE_REVIEW"

    def test_no_accept_possible_under_current_policy(self):
        face = FaceEvidence(similarity=1.0, match=True, threshold=0.0)
        doc = DocumentEvidence(
            mrz_valid=True, document_authentic=True,
            liveness_score=1.0, doc_type="passport")
        r = orchestrate(face, doc, PADState.VERIFIED)
        assert r.decision != KYCDecision.ACCEPT.value
        assert r.policy == "FORCE_REVIEW"

    def test_accept_requires_verified_under_any_policy(self):
        """ACCEPT ⟹ VERIFIED — the Phase 1 invariant, now at KYC level."""
        for pad in (PADState.HEURISTIC, PADState.UNAVAILABLE):
            face = FaceEvidence(similarity=1.0, match=True, threshold=0.0)
            doc = DocumentEvidence(
                mrz_valid=True, document_authentic=True,
                liveness_score=1.0, doc_type="passport")
            r = orchestrate(face, doc, pad, policy="TWO_THRESHOLD")
            assert r.decision != KYCDecision.ACCEPT.value
