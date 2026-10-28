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
