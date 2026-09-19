from ai.inference.pipeline import process_card

class AIService:
    @staticmethod
    def scan_card(image_bytes: bytes) -> dict:
        return process_card(image_bytes)