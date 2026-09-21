from pathlib import Path

class Settings:
    BASE_DIR = Path(__file__).resolve().parent.parent
    MODELS_DIR = BASE_DIR / "models"
    STORAGE_DIR = BASE_DIR / "storage"

    # OCR
    OCR_LANGUAGES = "ara+fra"
    OCR_PSM = 6
    OCR_OEM = 3

    # الوجه
    FACE_MODEL = "hog"
    FACE_THRESHOLD = 0.6
    FACE_NUM_JITTERS = 1

    # البطاقة
    CARD_ASPECT_RATIO_MIN = 1.3
    CARD_ASPECT_RATIO_MAX = 2.0
    CARD_MIN_AREA_RATIO = 0.3

    # التحقق
    MIN_IMAGE_SIZE = 200
    MAX_IMAGE_SIZE = 4096

settings = Settings()
