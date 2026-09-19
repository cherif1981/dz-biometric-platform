import httpx

from app.core.config import settings


class FaceService:
    def __init__(self):
        self.base_url = settings.ai_service_url

    async def encode(self, file_bytes: bytes, filename: str = "selfie.jpg") -> list:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                f"{self.base_url}/process",
                files={"file": (filename, file_bytes)},
            )
            r.raise_for_status()
            data = r.json()
            return data.get("face_encoding") or []