from app.services.face_service import FaceService
from app.services.ocr_service import OCRService


class VerificationService:
    def __init__(self):
        self.ocr = OCRService()
        self.face = FaceService()

    async def full_verify(
        self,
        card_bytes: bytes,
        selfie_bytes: bytes,
        card_filename: str = "card.jpg",
        selfie_filename: str = "selfie.jpg",
    ) -> dict:
        # 1. OCR على البطاقة
        ocr_result = await self.ocr.process(card_bytes, card_filename)

        # 2. مقارنة الوجه
        face_result = await self.face.verify(
            card_bytes, selfie_bytes, card_filename, selfie_filename
        )

        # 3. قرار نهائي بسيط
        verified = (
            ocr_result.get("success", False)
            and face_result.get("verified", False)
        )

        return {
            "status": "verified" if verified else "rejected",
            "document": {
                "success": ocr_result.get("success"),
                "fields": ocr_result.get("fields"),
                "confidence": ocr_result.get("confidence"),
                "validation": ocr_result.get("validation"),
            },
            "face": {
                "matched": face_result.get("verified"),
                "similarity": face_result.get("similarity"),
                "distance": face_result.get("distance"),
                "message": face_result.get("message"),
            },
            "processing_time": {
                "ocr": ocr_result.get("processing_time"),
                "face": face_result.get("processing_time"),
            },
        }