from src.ai.engine import BiometricAI


class FaceOK:
    def verify(self, id_image, selfie):
        return {"similarity": 0.91, "is_match": True}


class SpoofModelOK:
    def check(self, selfie):
        return {"score": 0.97, "is_real": True, "method": "minifasnet_v2"}


class SpoofHeuristic:
    def check(self, selfie):
        return {"score": 0.99, "is_real": True, "method": "heuristic_fallback"}


class FaceUnavailable:
    def verify(self, id_image, selfie):
        return {"similarity": 0.0, "is_match": False, "error": "face_model_unavailable"}


def test_assess_accepts_only_when_both_trained_services_pass():
    result = BiometricAI(FaceOK(), SpoofModelOK()).assess(b"id", b"selfie")
    assert result["accepted"] is True
    assert result["face"]["similarity"] == 0.91
    assert result["spoof"]["method"] == "minifasnet_v2"


def test_heuristic_fallback_is_not_accepted_as_anti_spoof_evidence():
    result = BiometricAI(FaceOK(), SpoofHeuristic()).assess(b"id", b"selfie")
    assert result["accepted"] is False
    assert result["spoof"]["available"] is False
    assert result["spoof"]["score"] is None


def test_missing_face_model_fails_closed():
    result = BiometricAI(FaceUnavailable(), SpoofModelOK()).assess(b"id", b"selfie")
    assert result["accepted"] is False
    assert result["face"]["available"] is False
    assert result["face"]["similarity"] is None


def test_invalid_spoof_score_fails_closed():
    class InvalidScore:
        def check(self, selfie):
            return {"score": float("nan"), "is_real": True, "method": "minifasnet_v2"}

    result = BiometricAI(FaceOK(), InvalidScore()).assess(b"id", b"selfie")
    assert result["accepted"] is False
    assert result["spoof"]["score"] is None
