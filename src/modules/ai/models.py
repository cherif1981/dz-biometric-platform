"""Data models for AI Risk Engine."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class RiskLevel(str, Enum):
    """مستوى المخاطر."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Decision(str, Enum):
    """القرار النهائي للتحقق."""
    VERIFIED = "VERIFIED"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    REJECTED = "REJECTED"


@dataclass
class RiskScore:
    """نتيجة محرك المخاطر."""
    score: float
    level: RiskLevel
    components: Dict[str, float] = field(default_factory=dict)
    model_version: str = "1.0.0"
    threshold_version: str = "1.0.0"

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "level": self.level.value,
            "components": self.components,
            "model_version": self.model_version,
            "threshold_version": self.threshold_version,
        }


@dataclass
class DecisionResult:
    """نتيجة محرك القرار."""
    decision: Decision
    risk: RiskScore
    reasons: List[str] = field(default_factory=list)
    raw_scores: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "decision": self.decision.value,
            "risk": self.risk.to_dict(),
            "reasons": self.reasons,
            "raw_scores": self.raw_scores,
        }
