"""OCRService adapter — wraps modules.ocr engines."""
from typing import Dict, Optional
from loguru import logger


class OCRService:
    def __init__(self, default_lang: str = "ar"):
        self.default_lang = default_lang

    def extract(self, image_bytes: bytes, lang: Optional[str] = None) -> Dict:
        lang = lang or self.default_lang
        try:
            if lang == "fr":
                from src.modules.ocr.french_engine import FrenchEngine
                r = FrenchEngine().read(image_bytes)
            else:
                from src.modules.ocr.arabic_engine import ArabicEngine
                r = ArabicEngine().read(image_bytes)
            return {
                "fields": r.get("fields", {}) or {},
                "confidence": float(r.get("confidence", 0.0)),
                "text": r.get("text", ""),
                "lang": lang,
            }
        except Exception as e:
            logger.error(f"OCRService.extract failed: {e}")
            raise
