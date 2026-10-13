"""AI Risk Engine — يحول الإشارات إلى risk_score موزون."""

from typing import Dict, Optional
from loguru import logger

from .models import RiskScore, RiskLevel


class RiskEngine:
    """
    محرك المخاطر الموحد.

    يستقبل إشارات التحقق (face_similarity, liveness, antispoof,
    ocr_confidence, document_tampering, face_quality) ويحولها
    إلى risk_score واحد مع مستوى ومساهمات لكل إشارة.
    """

    DEFAULT_WEIGHTS = {
        "face_similarity": 0.30,
        "face_quality": 0.05,
        "liveness": 0.22,
        "antispoof": 0.22,
        "ocr_confidence": 0.08,
        "document_tampering": 0.08,
        "document_quality": 0.05,
    }

    # الإشارات التي القيمة الأعلى فيها = أفضل (تُقلب عند حساب المخاطر)
    POSITIVE_SIGNALS = {
        "face_similarity",
        "face_quality",
        "liveness",
        "antispoof",
        "ocr_confidence",
        "document_quality",
    }

    RISK_THRESHOLDS = {
        RiskLevel.LOW:      0.25,
        RiskLevel.MEDIUM:   0.50,
        RiskLevel.HIGH:     0.75,
        RiskLevel.CRITICAL: 1.00,
    }

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        model_version: str = "1.0.0",
        threshold_version: str = "1.0.0",
    ):
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()

        # تطبيع الأوزان
        total = sum(self.weights.values())
        if total > 0:
            self.weights = {k: v / total for k, v in self.weights.items()}
        else:
            raise ValueError("مجموع الأوزان يجب أن يكون > 0")

        self.model_version = model_version
        self.threshold_version = threshold_version

        logger.info(
            f"RiskEngine initialized | weights={self.weights} | "
            f"model={model_version} | thresholds={threshold_version}"
        )

    def _classify_level(self, risk_score: float) -> RiskLevel:
        for lvl, threshold in sorted(self.RISK_THRESHOLDS.items(), key=lambda x: x[1]):
            if risk_score <= threshold:
                return lvl
        return RiskLevel.CRITICAL

    def compute(self, signals: Dict[str, float]) -> RiskScore:
        """
        Args:
            signals: dict {اسم الإشارة: القيمة بين 0 و 1}

        Returns:
            RiskScore
        """
        if not signals:
            logger.warning("RiskEngine.compute استُدعي بدون إشارات")
            return RiskScore(
                score=1.0,
                level=RiskLevel.CRITICAL,
                components={},
                model_version=self.model_version,
                threshold_version=self.threshold_version,
            )

        risk_components: Dict[str, float] = {}
        total_risk = 0.0
        total_weight_used = 0.0

        for signal, value in signals.items():
            if signal not in self.weights:
                logger.debug(f"إشارة غير معروفة تجاهلت: {signal}")
                continue

            weight = self.weights[signal]
            value = float(value)
            value = max(0.0, min(1.0, value))

            if signal in self.POSITIVE_SIGNALS:
                risk_value = 1.0 - value
            else:
                risk_value = value

            contribution = risk_value * weight
            risk_components[signal] = round(contribution, 4)
            total_risk += contribution
            total_weight_used += weight

        if total_weight_used > 0:
            risk_score = total_risk / total_weight_used
        else:
            risk_score = 1.0

        risk_score = round(risk_score, 4)
        level = self._classify_level(risk_score)

        return RiskScore(
            score=risk_score,
            level=level,
            components=risk_components,
            model_version=self.model_version,
            threshold_version=self.threshold_version,
        )
