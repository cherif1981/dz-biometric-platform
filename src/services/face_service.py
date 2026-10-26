
from typing import Dict
from src.services.base_service import BaseVerificationService

# ═══════════════════════════════════════════════════════════
# توافق خلفي: علم تحميل InsightFace (يستخدمه الاختبار)
# ═══════════════════════════════════════════════════════════
try:
    import insightface  # noqa: F401
    HAS_INSIGHT = True
except ImportError:
    HAS_INSIGHT = False

class FaceVerificationService(BaseVerificationService):
    modality = "face_similarity"

    def verify(self, payload: Dict) -> Dict[str, float]:
        # ⚠️ هنا مكان منطق مطابقة الوجه (embedding similarity).
        # المهم: تُرجع درجة فقط، لا تقارنها بأي عتبة.
        score = payload.get("face_score", 0.0)
        return {self.modality: float(score)}

    # ---- backward-compat singleton accessor ----
    _singleton = None

    @classmethod
    def get(cls):
        """Return a shared instance. Some legacy code calls FaceService.get()."""
        if cls._singleton is None:
            cls._singleton = cls()
        return cls._singleton


# ═══════════════════════════════════════════════════════════════════
# توافق خلفي: FaceService (يستخدمه الاختبار)
# ═══════════════════════════════════════════════════════════════════
class FaceService:
    """stub للتوافق — الكود الفعلي يستخدم AntispoofingService بدلًا منه."""
    def __init__(self, *args, **kwargs):
        self._ready = HAS_INSIGHT
    def verify(self, *args, **kwargs):
        return {"matched": False, "similarity": 0.0,
                "reason": "stub"}
