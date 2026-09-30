"""Face service — ترميز وكشف الوجوه."""
from typing import List


class FaceService:
    @staticmethod
    async def encode(image_bytes: bytes) -> List[float]:
        """Placeholder — يُستبدل في الاختبارات بـ AsyncMock."""
        return []

    @staticmethod
    async def detect(image_bytes: bytes) -> List[List[int]]:
        return []


face_service = FaceService()
