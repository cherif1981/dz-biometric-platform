import httpx

from app.core.config import settings


class OCRService:
    def __init__(self):
        self.base_url = settings.ai_service_url

    async def process(self, file_bytes: bytes, filename: str = "card.jpg") -> dict:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                f"{self.base_url}/process",
                files={"file": (filename, file_bytes)},
            )
            r.raise_for_status()
            return r.json()