"""PAD security invariants — Phase 1 (locked)."""
import os
import subprocess
import pytest
from anti_spoof.decision import (
    decide, decide_multimodal, PADState, Decision, POLICY,
)


class TestPadStateIsCanonical:
    """Exactly two canonical PADState definitions, each in its proper level.

    - Model level:   anti_spoof/decision.py    (VERIFIED/HEURISTIC/UNAVAILABLE)
    - Service level: src/services/antispoofing_service.py (VERIFIED/HEURISTIC/LOADED)

    - Session state lives in dz_service.py as `JobState` (NOT PADState).
    """

    def _grep_class_padstate(self):
        # Use `^class` anchor so comment/string mentions don't match.
        r = subprocess.run(
            ["grep", "-rnE", "--include=*.py", r"^class PADState", "."],
            capture_output=True, text=True,
        )
        lines = [l for l in r.stdout.splitlines()
                 if "_backup" not in l and not l.startswith("./tests/")]
        return lines

    def test_exactly_two_canonical_definitions(self):
        lines = self._grep_class_padstate()
        assert len(lines) == 2, f"expected 2 canonical defs, got {len(lines)}: {lines}"
        files = [l.split(":", 1)[0] for l in lines]
        assert any("anti_spoof/decision.py" in f for f in files), \
            f"missing model-level PADState: {files}"
        assert any("antispoofing_service.py" in f for f in files), \
            f"missing service-level PADState: {files}"

    def test_no_other_class_padstate_anywhere(self):
        """Only anti_spoof and antispoofing_service may define `class PADState`."""
        lines = self._grep_class_padstate()
        allowed = ("anti_spoof/decision.py", "antispoofing_service.py")
        for line in lines:
            assert any(a in line for a in allowed), \
                f"unexpected `class PADState` at: {line}"

    def test_dz_service_uses_jobstate_not_padstate(self):
        with open("dz_service.py") as f:
            s = f.read()
        assert "class PADState" not in s, \
            "dz_service must NOT define class PADState (use JobState + alias)"
        assert "class JobState" in s, "dz_service missing JobState class"
        assert "PADState = JobState" in s, "dz_service missing alias"

    def test_model_padstate_has_no_session_states(self):
        for forbidden in ("ACCEPTED", "REJECTED", "INITIATED", "MATCHING"):
            assert not hasattr(PADState, forbidden), \
                f"model PADState polluted with session state {forbidden}"

    def test_service_padstate_retains_loaded(self):
        """The service-level enum must keep LOADED (contract requirement)."""
        from src.services.antispoofing_service import PADState as ServicePADState
        assert hasattr(ServicePADState, "LOADED"), \
            "service PADState lost LOADED — regression against contract test"

    def test_bridge_file_exists(self):
        assert os.path.exists("src/services/pad_state_bridge.py")

class TestNoAcceptWithoutVerified:
    @pytest.mark.parametrize("state", [PADState.HEURISTIC, PADState.UNAVAILABLE])
    @pytest.mark.parametrize("score", [0.0, 0.5, 0.85, 0.99, 1.0, None])
    def test_decide_never_accepts_non_verified(self, state, score):
        assert decide(score, state) != Decision.ACCEPT


class TestIsLiveMatchesDecision:
    def test_no_raw_threshold_is_live(self):
        r = subprocess.run(
            ["grep", "-rn", "--include=*.py", r"is_live.*score.*>=", "."],
            capture_output=True, text=True)
        v = [l for l in r.stdout.splitlines()
             if "_backup" not in l and "/tests/" not in l]
        assert not v, f"raw-threshold is_live: {v}"

    def test_biometric_ai_uses_helper(self):
        with open("src/modules/ai/biometric_ai.py") as f: s = f.read()
        assert "_derive_is_live_from_decision" in s
        assert "is_live=score >= 0.50" not in s


class TestForceReviewIsAbsolute:
    def test_decide_multimodal_has_guard(self):
        import inspect
        src = inspect.getsource(decide_multimodal)
        assert 'if POLICY == "FORCE_REVIEW":' in src

    @pytest.mark.skipif(POLICY != "FORCE_REVIEW", reason="policy inactive")
    def test_verified_still_reviewed(self):
        assert decide(0.99, PADState.VERIFIED) == Decision.REVIEW
