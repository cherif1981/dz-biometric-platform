"""OCR service — يستدعي AI Service."""
from app.services.ai_client import AIService


class OCRService:
    @staticmethod
    async def process(image_bytes: bytes) -> dict:
        """Placeholder — يُستبدل في الاختبارات."""
        return AIService.scan_card(image_bytes)


ocr_service = OCRService()
