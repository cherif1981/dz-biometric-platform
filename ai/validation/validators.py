import numpy as np
from typing import Tuple
from ai.configs.settings import settings

class ImageValidator:
    def validate(self, image: np.ndarray) -> Tuple[bool, str]:
        if image is None or image.size == 0:
            return False, "الصورة فارغة"
        h, w = image.shape[:2]
        if min(h, w) < settings.MIN_IMAGE_SIZE:
            return False, f"الصورة صغيرة جداً ({w}x{h})"
        if max(h, w) > settings.MAX_IMAGE_SIZE:
            return False, f"الصورة كبيرة جداً ({w}x{h})"
        if image.std() < 5:
            return False, "الصورة منخفضة التباين"
        return True, "صورة صالحة"

class ResultValidator:
    def validate_ocr(self, fields: dict) -> dict:
        issues = []
        if not fields.get("nin"):
            issues.append("لم يتم استخراج رقم التعريف الوطني")
        if not fields.get("nom"):
            issues.append("لم يتم استخراج اللقب")
        if not fields.get("prenom"):
            issues.append("لم يتم استخراج الاسم")
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "completeness": sum(1 for v in fields.values() if v) / len(fields) * 100
        }
