"""AI Report Builder — تقرير موحد من كل طبقات AI."""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from loguru import logger


# إصدار سكيما التقرير (للتتبع مع مرور الوقت)
REPORT_SCHEMA_VERSION = "1.0.0"


@dataclass
class AIReport:
    """تقرير موحد للتحقق."""
    decision: str
    risk: Dict[str, Any]
    face: Dict[str, Any] = field(default_factory=dict)
    liveness: Dict[str, Any] = field(default_factory=dict)
    antispoof: Dict[str, Any] = field(default_factory=dict)
    document: Dict[str, Any] = field(default_factory=dict)
    models: Dict[str, str] = field(default_factory=dict)
    thresholds: Dict[str, Any] = field(default_factory=dict)
    reasons: list = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "decision": self.decision,
            "risk": self.risk,
            "face": self.face,
            "liveness": self.liveness,
            "antispoof": self.antispoof,
            "document": self.document,
            "models": self.models,
            "thresholds": self.thresholds,
            "reasons": self.reasons,
            "meta": self.meta,
        }


class ReportBuilder:
    """
    يبني تقرير AI الموحد من مخرجات RiskEngine + DecisionEngine +
    DocumentAI + BiometricAI.
    """

    def __init__(
        self,
        schema_version: str = REPORT_SCHEMA_VERSION,
        include_meta: bool = True,
    ):
        self.schema_version = schema_version
        self.include_meta = include_meta
        logger.info(f"ReportBuilder initialized | schema={schema_version}")

    def build(
        self,
        decision_result,                       # DecisionResult
        signals: Dict[str, float],
        doc_analysis=None,                     # DocumentAnalysis
        face_quality=None,                     # FaceQualityResult
        liveness_result=None,                  # LivenessResult
        antispoof_result=None,                 # AntiSpoofResult
        extra_meta: Optional[Dict[str, Any]] = None,
    ) -> AIReport:
        risk = decision_result.risk

        # ===== risk =====
        risk_block = {
            "score": round(float(risk.score), 4),
            "level": risk.level.value,
            "components": {k: round(float(v), 4) for k, v in risk.components.items()},
        }

        # ===== face =====
        face_block = {
            "similarity": round(float(signals.get("face_similarity", 0.0)), 4),
            "quality": round(float(signals.get("face_quality", 0.0)), 4),
        }
        if face_quality is not None:
            face_block["quality_details"] = {
                "sharpness": face_quality.sharpness,
                "brightness": face_quality.brightness,
                "contrast": face_quality.contrast,
                "face_size": face_quality.face_size,
                "pose": face_quality.pose_score,
                "acceptable": face_quality.is_acceptable,
            }

        # ===== liveness =====
        liveness_block = {
            "score": round(float(signals.get("liveness", 0.0)), 4),
            "method": liveness_result.method if liveness_result else "unknown",
        }
        if liveness_result is not None and liveness_result.details:
            liveness_block["details"] = liveness_result.details

        # ===== antispoof =====
        antispoof_block = {
            "score": round(float(signals.get("antispoof", 0.0)), 4),
            "method": antispoof_result.method if antispoof_result else "unknown",
        }
        if antispoof_result is not None and antispoof_result.details:
            antispoof_block["details"] = antispoof_result.details

        # ===== document =====
        doc_block = {
            "type": doc_analysis.doc_type if doc_analysis else "unknown",
            "type_confidence": round(float(
                doc_analysis.type_confidence if doc_analysis else 0.0), 4),
            "quality": round(float(
                doc_analysis.quality_score if doc_analysis else 0.0), 4),
            "ocr_confidence": round(float(signals.get("ocr_confidence", 0.0)), 4),
            "tampering_probability": round(float(
                doc_analysis.tampering_probability if doc_analysis else 0.0), 4),
            "field_consistency": round(float(
                doc_analysis.field_consistency if doc_analysis else 0.0), 4),
        }
        if doc_analysis is not None and doc_analysis.extracted_fields:
            # احجب بعض الحقول الحساسة في التقرير العام
            fields = dict(doc_analysis.extracted_fields)
            for sensitive in ("document_number", "passport_number", "license_number"):
                if sensitive in fields:
                    val = fields[sensitive]
                    fields[sensitive] = (val[:2] + "***" + val[-2:]) if len(val) > 4 else "***"
            doc_block["extracted_fields_masked"] = fields

        # ===== models =====
        models_block = {
            "face": "buffalo_l",
            "liveness": liveness_result.method if liveness_result else "heuristic_v1",
            "antispoof": antispoof_result.method if antispoof_result else "heuristic_v1",
            "document_ai": "heuristic_v1",
            "risk_engine": risk.model_version,
        }

        # ===== thresholds =====
        thresholds_block = {
            "version": risk.threshold_version,
        }

        # ===== reasons =====
        reasons = list(decision_result.reasons or [])
        if doc_analysis is not None and doc_analysis.reasons:
            reasons.extend([f"DOC:{r}" for r in doc_analysis.reasons])
        if face_quality is not None and face_quality.reasons:
            reasons.extend([f"FACE:{r}" for r in face_quality.reasons])

        # ===== meta =====
        meta_block = {}
        if self.include_meta:
            meta_block = {
                "schema_version": self.schema_version,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "report_version": risk.model_version,
            }
            if extra_meta:
                meta_block.update(extra_meta)

        return AIReport(
            decision=decision_result.decision.value,
            risk=risk_block,
            face=face_block,
            liveness=liveness_block,
            antispoof=antispoof_block,
            document=doc_block,
            models=models_block,
            thresholds=thresholds_block,
            reasons=reasons,
            meta=meta_block,
        )
