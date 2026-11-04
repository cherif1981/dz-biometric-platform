# SECURITY NOTE (2026-11):
# FORCE_REVIEW is the policy default. Do NOT lower it based on synthetic
# attacks (blur/noise) — they underestimate the true attack surface.
# APCER/BPCER must be measured on real presentation attacks per
# ISO/IEC 30107-3 before relaxing this policy.
#
# STATUS: this module (decide_multimodal + sanity + blink) is NOT called
# from the main verification path (src/services/antispoofing_service.py).
# It exists as a parallel implementation. Wiring it in should be a
# separate PR, and must fail-closed on any missing/errored signal.
"""Safe decision gate - FORCE_REVIEW.

No local model achieves AUC >= 0.85 on real attack data.
All HEURISTIC decisions go to REVIEW. Never ACCEPT.
"""
from enum import Enum


class ModelStatus(str, Enum):
    VERIFIED = "VERIFIED"
    HEURISTIC = "HEURISTIC"
    UNAVAILABLE = "UNAVAILABLE"


class Decision(str, Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    REVIEW = "REVIEW"


# Real-data evaluation (Kaggle web-camera-face-liveness):
#   MiniFASNetV2   AUC=0.6405  -> fail
#   MiniFASNetV1SE AUC=0.6257  -> fail
#   facenox_SE     AUC=0.5387  -> fail
#   ResNet50_LR    AUC=0.7937 (var=0.19) -> insufficient
MODEL_EVALUATIONS = {
    "MiniFASNetV2": 0.6405,
    "MiniFASNetV1SE": 0.6257,
    "facenox_SE": 0.5387,
    "ResNet50_LR": 0.7937,
}
MIN_ACCEPTABLE_AUC = 0.85
BEST_AUC = max(MODEL_EVALUATIONS.values())
POLICY = "FORCE_REVIEW" if BEST_AUC < MIN_ACCEPTABLE_AUC else "TWO_THRESHOLD"


def decide(liveness, status):
    """Every request goes to REVIEW until a model achieves AUC >= 0.85."""
    if liveness is None or status == ModelStatus.UNAVAILABLE:
        return Decision.REVIEW
    if status == ModelStatus.HEURISTIC or POLICY == "FORCE_REVIEW":
        return Decision.REVIEW
    return Decision.REVIEW


from .sanity import sanity_check
from .blink import detect_blink


def decide_multimodal(frames, pad_score, pad_status):
    """قرار متعدد الطبقات: sanity + PAD + رمشة."""
    if not frames:
        return Decision.REVIEW, "no_frames"
    ok, reason = sanity_check(frames[0])
    if not ok:
        return Decision.REJECT, f"sanity:{reason}"
    if pad_score is None or pad_status == ModelStatus.UNAVAILABLE:
        return Decision.REVIEW, "pad_unavailable"
    blinked, _ = detect_blink(frames)
    if not blinked:
        return Decision.REJECT, "no_blink_static_attack"
    if pad_score >= 0.85 and pad_status == ModelStatus.VERIFIED:
        return Decision.ACCEPT, "all_layers_passed"
    return Decision.REVIEW, f"pad_borderline:{pad_score:.3f}"
