"""Face match service tests — unit (mocked) + integration (real model).

Slow tests are marked `requires_model` and skipped unless FACE_MATCH_RUN_SLOW=1.
"""
import os
import numpy as np
import pytest

from src.services.face_match_service import FaceMatchService

RUN_SLOW = os.getenv("FACE_MATCH_RUN_SLOW", "0") == "1"
requires_model = pytest.mark.skipif(not RUN_SLOW, reason="set FACE_MATCH_RUN_SLOW=1")


def _key(img) -> bytes:
    """Stable key for both bytes and ndarray inputs."""
    if isinstance(img, (bytes, bytearray)):
        return bytes(img)[:8]
    return img.tobytes()[:8]


# ═══ Unit tests (no model) ═══════════════════════════════════════════
class TestFaceMatchUnit:
    def _make_service(self, embeddings: dict):
        svc = FaceMatchService(threshold=0.35)
        svc._ensure_loaded = lambda: None

        def fake_extract(img):
            k = _key(img)
            if k not in embeddings:
                raise KeyError(f"unexpected image key {k!r}; known: {list(embeddings)}")
            return embeddings[k]

        svc._extract = fake_extract
        return svc

    def test_identical_embeddings_match(self):
        e = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        svc = self._make_service({
            b"AAAA\x00\x00\x00\x00": e,
            b"BBBB\x00\x00\x00\x00": e,
        })
        r = svc.match(b"AAAA\x00\x00\x00\x00", b"BBBB\x00\x00\x00\x00")
        assert r["match"] is True
        assert r["similarity"] == pytest.approx(1.0, abs=1e-5)

    def test_orthogonal_embeddings_no_match(self):
        a = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        b = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        svc = self._make_service({
            b"AAAA\x00\x00\x00\x00": a,
            b"BBBB\x00\x00\x00\x00": b,
        })
        r = svc.match(b"AAAA\x00\x00\x00\x00", b"BBBB\x00\x00\x00\x00")
        assert r["match"] is False
        assert r["similarity"] == pytest.approx(0.0, abs=1e-5)

    def test_threshold_respected(self):
        a = np.array([1.0, 0.0], dtype=np.float32)
        b = np.array([0.866, 0.5], dtype=np.float32)  # cos ~ 0.866
        svc = self._make_service({
            b"AAAA\x00\x00\x00\x00": a,
            b"BBBB\x00\x00\x00\x00": b,
        })
        # high threshold → no match
        assert svc.match(b"AAAA\x00\x00\x00\x00",
                         b"BBBB\x00\x00\x00\x00",
                         threshold=0.95)["match"] is False
        # low threshold → match
        assert svc.match(b"AAAA\x00\x00\x00\x00",
                         b"BBBB\x00\x00\x00\x00",
                         threshold=0.50)["match"] is True

    def test_empty_image_rejected(self):
        svc = FaceMatchService(threshold=0.35)
        svc._ensure_loaded = lambda: None
        with pytest.raises(ValueError, match="empty image"):
            svc.similarity(None, None)


# ═══ Integration with FORCE_REVIEW policy ════════════════════════════
class TestFaceMatchRespectsForceReview:
    """Phase 1 invariant: face_match=True cannot yield ACCEPT under FORCE_REVIEW."""

    def test_policy_blocks_accept_even_when_face_matches(self):
        from anti_spoof.decision import POLICY, PADState, Decision, decide
        if POLICY != "FORCE_REVIEW":
            pytest.skip("policy not active")
        assert decide(0.99, PADState.VERIFIED) == Decision.REVIEW

    def test_face_match_does_not_bypass_decision_engine(self):
        from anti_spoof.decision import decide, PADState, Decision, POLICY
        if POLICY != "FORCE_REVIEW":
            pytest.skip("policy not active")

        def orchestrator(face_sim, pad_state):
            d = decide(face_sim, pad_state)
            return {"accept": d == Decision.ACCEPT, "decision": d.name}

        assert orchestrator(1.0, PADState.VERIFIED)["accept"] is False
        assert orchestrator(1.0, PADState.HEURISTIC)["accept"] is False
        assert orchestrator(1.0, PADState.UNAVAILABLE)["accept"] is False


# ═══ Slow integration (real model) ══════════════════════════════════
@requires_model
class TestFaceMatchRealModel:
    def test_real_model_loads_and_embeds(self):
        svc = FaceMatchService()
        svc._ensure_loaded()
        assert svc._app is not None
