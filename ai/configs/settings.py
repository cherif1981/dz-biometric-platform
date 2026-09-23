from pathlib import Path

class Settings:
    BASE_DIR = Path(__file__).resolve().parent.parent
    MODELS_DIR = BASE_DIR / "models"
    STORAGE_DIR = BASE_DIR / "storage"

    # OCR
    OCR_LANGUAGES = "ara+fra"
    OCR_PSM = 6
    OCR_OEM = 3

    # ===== Face Recognition (محسّن) =====
    FACE_MODEL = "cnn"              # أدق من hog (يحتاج GPU أفضل، أو يبقى hog)
    FACE_ENCODING_MODEL = "large"   # أدق من small
    FACE_THRESHOLD = 0.55           # أكثر تشدداً (كان 0.6)
    FACE_NUM_JITTERS = 3            # زيادة الدقة (كان 1)
    FACE_MIN_SIZE = 80              # أقل حجم مقبول للوجه بالبكسل
    FACE_UPSAMPLE = 1               # يساعد في اكتشاف الوجوه الصغيرة

    # البطاقة
    CARD_ASPECT_RATIO_MIN = 1.3
    CARD_ASPECT_RATIO_MAX = 2.0
    CARD_MIN_AREA_RATIO = 0.3

    # التحقق
    MIN_IMAGE_SIZE = 200
    MAX_IMAGE_SIZE = 4096

settings = Settings()