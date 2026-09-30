"""HTTP client for the AI Service."""
import os
import httpx


AI_SERVICE_URL = os.environ.get("AI_SERVICE_URL", "http://localhost:8001")
AI_SERVICE_TIMEOUT = float(os.environ.get("AI_SERVICE_TIMEOUT", "60"))


class AIService:
    @staticmethod
    def scan_card(image_bytes: bytes) -> dict:
        url = f"{AI_SERVICE_URL}/internal/ocr/extract"
        files = {"file": ("card.jpg", image_bytes, "image/jpeg")}
        with httpx.Client(timeout=AI_SERVICE_TIMEOUT) as client:
            r = client.post(url, files=files)
            r.raise_for_status()
            return r.json()
