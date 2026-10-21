"""Anti-spoofing service + adapter."""
from typing import Dict
from loguru import logger

from src.services.base_service import BaseVerificationService


class AntispoofingService(BaseVerificationService):
    modality = "antispoofing"

    def verify(self, payload: Dict) -> Dict[str, float]:
        score = payload.get("antispoofing_score", 0.0)
        return {self.modality: float(score)}


class AntiSpoofing:
    """Adapter for VerificationEngine.

    API: instance.check(image_bytes) -> {"score": float, "is_real": bool, ...}
    """
    def __init__(self, threshold: float = 0.45):
        self.threshold = float(threshold)
        self._impl = None
        self._resolved = False

    def _resolve_backend(self):
        if self._resolved:
            return
        self._resolved = True
        candidates = [
            ("src.modules.antispoofing.passive", "PassiveAntiSpoof"),
            ("src.modules.anti_spoofing.passive", "PassiveAntiSpoof"),
            ("src.modules.antispoofing.detector", "AntiSpoofDetector"),
        ]
        for mod_path, cls_name in candidates:
            try:
                mod = __import__(mod_path, fromlist=[cls_name])
                cls = getattr(mod, cls_name, None)
                if cls is not None:
                    self._impl = cls()
                    logger.info(f"AntiSpoofing backend: {mod_path}.{cls_name}")
                    return
            except Exception:
                continue
        logger.warning("AntiSpoofing: no backend — using pass-through stub")

    def check(self, image_bytes: bytes) -> Dict:
        self._resolve_backend()
        if self._impl is None:
            return {"score": 1.0, "is_real": True, "stub": True}
        r = self._impl.predict(image_bytes)
        if isinstance(r, dict):
            score = float(r.get("score", r.get("real_prob", r.get("confidence", 0.0))))
            return {"score": score, "is_real": score >= self.threshold, **r}
        return {"score": float(r), "is_real": float(r) >= self.threshold}


# backward-compat aliases for old imports
Antispoofing = AntispoofingService
