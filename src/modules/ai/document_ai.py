"""Document AI — تصنيف، جودة، كشف تلاعب، استخراج حقول."""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional
import re

import cv2
import numpy as np
from loguru import logger


@dataclass
class DocumentAnalysis:
    """نتيجة تحليل الوثيقة."""
    doc_type: str = "unknown"
    type_confidence: float = 0.0
    quality_score: float = 0.0
    tampering_probability: float = 0.0
    extracted_fields: Dict[str, str] = field(default_factory=dict)
    field_consistency: float = 0.0
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "doc_type": self.doc_type,
            "type_confidence": self.type_confidence,
            "quality_score": self.quality_score,
            "tampering_probability": self.tampering_probability,
            "extracted_fields": self.extracted_fields,
            "field_consistency": self.field_consistency,
            "reasons": self.reasons,
        }


class DocumentAI:
    """
    Document AI Layer.

    - تصنيف نوع الوثيقة (heuristic → يمكن استبداله بنموذج CNN)
    - تقييم الجودة (Laplacian sharpness + brightness + contrast)
    - كشف التلاعب (Error Level Analysis + Edge anomaly)
    - استخراج الحقول + فحص الاتساق
    """

    # الحقول المطلوبة لكل نوع وثيقة (قابلة للتوسيع)
    REQUIRED_FIELDS = {
        "national_id":    ["first_name", "last_name", "date_of_birth", "document_number"],
        "passport":       ["first_name", "last_name", "date_of_birth", "passport_number", "nationality"],
        "driver_license": ["first_name", "last_name", "date_of_birth", "license_number"],
        "unknown":        ["first_name", "last_name"],
    }

    # أنماط للتحقق من صحة الحقول
    FIELD_PATTERNS = {
        "date_of_birth": r"^\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}$",
        "document_number": r"^[A-Z0-9]{5,20}$",
        "passport_number": r"^[A-Z0-9]{6,15}$",
        "license_number":  r"^[A-Z0-9]{5,20}$",
    }

    def __init__(self, ocr_service=None, min_quality: float = 0.30):
        self.ocr = ocr_service
        self.min_quality = min_quality
        logger.info("DocumentAI initialized (heuristic_v1)")

    # ==================== الواجهة العامة ====================
    def analyze(self, image_bytes: bytes) -> DocumentAnalysis:
        reasons: List[str] = []

        # 1. فك ترميز الصورة
        img = self._decode(image_bytes)
        if img is None:
            reasons.append("INVALID_IMAGE")
            return DocumentAnalysis(reasons=reasons)

        # 2. تقييم الجودة
        quality = self._assess_quality(img)
        if quality < self.min_quality:
            reasons.append(f"LOW_QUALITY:{quality:.3f}")

        # 3. تصنيف النوع
        doc_type, type_conf = self._classify_document(img)

        # 4. كشف التلاعب
        tampering = self._detect_tampering(img)
        if tampering > 0.6:
            reasons.append(f"TAMPERING_SUSPECTED:{tampering:.3f}")

        # 5. استخراج الحقول (إن وُجد OCR)
        fields = {}
        if self.ocr is not None:
            try:
                fields = self._extract_fields(image_bytes)
            except Exception as e:
                logger.warning(f"OCR failed: {e}")
                reasons.append("OCR_FAILED")

        # 6. الاتساق
        consistency = self._check_consistency(fields, doc_type)
        if consistency < 0.5 and fields:
            reasons.append(f"LOW_CONSISTENCY:{consistency:.3f}")

        return DocumentAnalysis(
            doc_type=doc_type,
            type_confidence=type_conf,
            quality_score=quality,
            tampering_probability=tampering,
            extracted_fields=fields,
            field_consistency=consistency,
            reasons=reasons,
        )

    # ==================== داخلي ====================
    @staticmethod
    def _decode(image_bytes: bytes):
        try:
            arr = np.frombuffer(image_bytes, np.uint8)
            return cv2.imdecode(arr, cv2.IMREAD_COLOR)
        except Exception as e:
            logger.error(f"Decode failed: {e}")
            return None

    def _assess_quality(self, img) -> float:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # حدة (Laplacian variance)
        sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
        sharpness_score = min(1.0, sharpness / 500.0)

        # إضاءة
        brightness = float(np.mean(gray)) / 255.0
        brightness_score = 1.0 - abs(brightness - 0.5) * 2.0
        brightness_score = max(0.0, brightness_score)

        # تباين
        contrast = float(gray.std()) / 128.0
        contrast_score = min(1.0, contrast)

        quality = (sharpness_score * 0.4
                   + brightness_score * 0.3
                   + contrast_score * 0.3)

        return round(float(quality), 4)

    def _classify_document(self, img) -> tuple:
        """تصنيف heuristic بناءً على الأبعاد + النسبة."""
        h, w = img.shape[:2]
        aspect = w / h if h > 0 else 1.0

        # قيم تقريبية لأنواع الوثائق
        if aspect > 1.3:
            return "national_id", 0.70
        elif 1.0 <= aspect <= 1.3:
            return "driver_license", 0.55
        elif aspect < 0.9:
            return "passport", 0.60
        return "unknown", 0.30

    def _detect_tampering(self, img) -> float:
        """
        كشف تلاعب heuristic:
        - ELA (Error Level Analysis): ضغط JPEG ثم قياس الفرق
        - Edge anomaly: كثافة حواف غير طبيعية
        """
        try:
            # ELA
            _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 90])
            compressed = cv2.imdecode(buf, cv2.IMREAD_COLOR)
            diff = cv2.absdiff(img, compressed)
            ela_score = float(np.mean(diff)) / 255.0
            ela_prob = min(1.0, ela_score * 5.0)

            # Edge anomaly
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            edge_density = float(np.mean(edges)) / 255.0
            edge_prob = 0.0
            if edge_density > 0.15:
                edge_prob = min(1.0, (edge_density - 0.15) * 5.0)

            # Block artifact (JPEG)
            block_score = self._block_artifact_score(gray)

            # مزيج موزون
            tampering = (ela_prob * 0.5
                         + edge_prob * 0.3
                         + block_score * 0.2)

            return round(float(min(1.0, tampering)), 4)
        except Exception as e:
            logger.warning(f"Tampering detection failed: {e}")
            return 0.0

    @staticmethod
    def _block_artifact_score(gray) -> float:
        """يكتشف كتل JPEG 8x8 غير طبيعية (علامة على إعادة حفظ)."""
        try:
            h, w = gray.shape
            if h < 32 or w < 32:
                return 0.0
            # قياس التباين عبر حدود الكتل 8x8
            diffs = []
            for y in range(8, h - 8, 8):
                row = gray[y, :].astype(np.float32)
                row_above = gray[y - 1, :].astype(np.float32)
                diffs.append(np.abs(row - row_above).mean())
            if not diffs:
                return 0.0
            score = float(np.mean(diffs)) / 255.0
            return min(1.0, score * 8.0)
        except Exception:
            return 0.0

    def _extract_fields(self, image_bytes: bytes) -> Dict[str, str]:
        """يستدعي OCR service ويستخرج حقولاً منظمة."""
        result = self.ocr.extract(image_bytes) if hasattr(self.ocr, "extract") else {}
        # OCR service قد يعيد {"fields": {...}} أو مباشرة dict
        if isinstance(result, dict):
            fields = result.get("fields") or result
        else:
            fields = {}

        # تطبيع
        normalized = {}
        for k, v in (fields or {}).items():
            key = str(k).strip().lower().replace(" ", "_")
            val = str(v).strip() if v is not None else ""
            if val:
                normalized[key] = val
        return normalized

    def _check_consistency(self, fields: Dict[str, str], doc_type: str) -> float:
        """قياس اكتمال + صحة صيغة الحقول."""
        if not fields:
            return 0.0

        required = self.REQUIRED_FIELDS.get(doc_type, self.REQUIRED_FIELDS["unknown"])

        # 1. الاكتمال
        present = [f for f in required if fields.get(f)]
        completeness = len(present) / max(len(required), 1)

        # 2. صحة الصيغة
        valid = 0
        checked = 0
        for field_name, pattern in self.FIELD_PATTERNS.items():
            if fields.get(field_name):
                checked += 1
                if re.match(pattern, fields[field_name], re.IGNORECASE):
                    valid += 1
        format_score = (valid / checked) if checked > 0 else 1.0

        # 3. اتساق الاسم (لا أرقام في الأسماء)
        name_score = 1.0
        for name_field in ("first_name", "last_name"):
            val = fields.get(name_field, "")
            if val and any(ch.isdigit() for ch in val):
                name_score = 0.0
                break

        consistency = completeness * 0.5 + format_score * 0.3 + name_score * 0.2
        return round(float(consistency), 4)
