"""Safe decision gate - FORCE_REVIEW.

No local model achieves AUC >= 0.85 on real attack data.
All HEURISTIC decisions go to REVIEW. Never ACCEPT.
"""
from enum import Enum

# -- Security policy: never bypass FORCE_REVIEW unless model is scientifically verified --
import os as _os
MODEL_VERIFIED = _os.getenv('MODEL_VERIFIED', 'false').lower() == 'true'



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
POLICY = ("FORCE_REVIEW" if (BEST_AUC < MIN_ACCEPTABLE_AUC or not MODEL_VERIFIED) else "TWO_THRESHOLD")


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
