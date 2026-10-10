class AntiSpoofing:
    """Hook for real anti-spoofing models (e.g., Silent-Face-Anti-Spoofing)."""

    def check(self, image_bytes: bytes) -> dict:
        # Placeholder — integrate a trained model here
        return {"spoof": False, "score": 0.0}