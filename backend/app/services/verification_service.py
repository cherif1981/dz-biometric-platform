import httpx

from app.core.config import settings


class VerificationService:
    def __init__(self):
        self.base_url = settings.ai_service_url

    async def compare(self, enc1: list, enc2: list) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{self.base_url}/face/compare",
                json={"encoding1": enc1, "encoding2": enc2},
            )
            r.raise_for_status()
            return r.json()