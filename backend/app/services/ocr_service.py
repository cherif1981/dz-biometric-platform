import httpx
from app.core.config import settings


class OCRService:
    def __init__(self):
        self.base_url = settings.ai_service_url.rstrip("/")

    async def process(self, file_bytes: bytes, filename: str = "card.jpg") -> dict:
        async with httpx.AsyncClient(timeout=120.0) as client:
            files = {"file": (filename, file_bytes, "image/jpeg")}
            response = await client.post(
                f"{self.base_url}/api/v1/ocr/extract",
                files=files,
            )
            response.raise_for_status()
            return response.json()