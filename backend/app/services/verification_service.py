"""Verification service — منطق التحقق البيومتري."""
from app.repositories.verification_repository import VerificationRepository
from app.services.face_service import FaceService


class VerificationService:
    def __init__(self, repo: VerificationRepository):
        self.repo = repo
        self.face = FaceService()

    async def verify_face(self, image_bytes: bytes) -> dict:
        """
        يُرجع نتيجة التحقق — بدون تسريب face_encoding.
        """
        encoding = await self.face.encode(image_bytes)
        if not encoding:
            return {"success": False, "face_detected": False}

        return {
            "success": True,
            "face_detected": True,
            # "encoding" محذوف عمدًا
        }
