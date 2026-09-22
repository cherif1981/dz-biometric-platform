"""إعدادات Face Verification"""

MODEL_NAME = "buffalo_l"
DET_SIZE = (640, 640)
DEFAULT_THRESHOLD = 0.35

THRESHOLDS = {
    "high_security": 0.45,
    "medium_security": 0.35,
    "low_security": 0.25,
}

MIN_FACE_QUALITY = 0.3