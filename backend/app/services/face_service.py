import httpx
from app.core.config import settings


class FaceService:
    def __init__(self):
        self.base_url = settings.ai_service_url.rstrip("/")

    async def detect(self, file_bytes: bytes, filename: str = "face.jpg") -> dict:
        async with httpx.AsyncClient(timeout=60.0) as client:
            files = {"file": (filename, file_bytes, "image/jpeg")}
            response = await client.post(
                f"{self.base_url}/api/v1/face/detect",
                files=files,
            )
            response.raise_for_status()
            return response.json()

    async def verify(
        self,
        card_bytes: bytes,
        selfie_bytes: bytes,
        card_filename: str = "card.jpg",
        selfie_filename: str = "selfie.jpg",
    ) -> dict:
        async with httpx.AsyncClient(timeout=60.0) as client:
            files = {
                "card_image": (card_filename, card_bytes, "image/jpeg"),
                "selfie_image": (selfie_filename, selfie_bytes, "image/jpeg"),
            }
            response = await client.post(
                f"{self.base_url}/api/v1/face/verify",
                files=files,
            )
            response.raise_for_status()
            return response.json()