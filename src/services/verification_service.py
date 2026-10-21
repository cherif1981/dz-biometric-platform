from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any
from loguru import logger
import time
# === AI Risk Engine (Phase 1) ===
from src.modules.ai import RiskEngine, DecisionEngine, DocumentAI, BiometricAI, ReportBuilder
# === end ===



class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    MANUAL_REVIEW = "MANUAL_REVIEW"


@dataclass
class VerificationResult:
    status: VerificationStatus
    confidence: float
    face_similarity: Optional[float] = None
    liveness_score: Optional[float] = None
    antispoof_score: Optional[float] = None
    ocr_fields: Dict[str, Any] = field(default_factory=dict)
    reasons: List[str] = field(default_factory=list)
    scores: Dict[str, float] = field(default_factory=dict)
    audit_id: Optional[int] = None
    ai_report: Optional[Dict[str, Any]] = None


class VerificationEngine:
    def __init__(self, ft=None, lt=None, ast=None):
        from src.core.config import settings
        ft = ft if ft is not None else settings.thresholds["face_similarity"]
        lt = lt if lt is not None else settings.thresholds["liveness"]
        ast = ast if ast is not None else settings.thresholds["antispoofing"]

        from src.services.face_service import FaceService
        from src.services.liveness_service import LivenessService
        from src.services.ocr_service import OCRService
        from src.services.antispoofing_service import AntiSpoofing
        from src.services.audit_db import AuditDB

        self.face = FaceService.get()
        self.liveness = LivenessService()
        self.ocr = OCRService()
        self.antispoof = AntiSpoofing(ast)
        self.db = AuditDB()

        self.document_ai = DocumentAI(ocr_service=self.ocr)
        self.biometric_ai = BiometricAI(face_app=self.face)
        self.report_builder = ReportBuilder()
        self.risk_engine = RiskEngine()
        self.decision_engine = DecisionEngine()

        self.ft, self.lt, self.ast, self.band = ft, lt, ast, 0.10

    def verify(self, id_bytes, selfie_bytes, expected=None, client_ip=None):
        reasons, scores, ocr_fields = [], {}, {}
        fs = ls = asc = None
        try:
            o = self.ocr.extract(id_bytes)
            ocr_fields = o.get("fields", {})
            scores["ocr_confidence"] = float(o.get("confidence", 0))
            if not ocr_fields:
                reasons.append("OCR_FAILED")
        except Exception as e:
            return self._fin(VerificationStatus.REJECTED, 0, None, None, None,
                             {}, [f"OCR_ERROR:{e}"], {}, client_ip)
        try:
            ar = self.antispoof.check(selfie_bytes)
            asc = float(ar.get("score", 0))
            scores["antispoof"] = asc
            if not ar.get("is_real", False):
                reasons.append(f"SPOOF:{asc:.3f}")
        except Exception as e:
            reasons.append(f"ANTISPOOF_ERR:{e}")
        try:
            fr = self.face.verify(id_bytes, selfie_bytes)
            fs = float(fr.get("similarity", 0))
            scores["face_similarity"] = fs
            if fs < self.ft:
                reasons.append(f"FACE:{fs:.3f}")
        except Exception as e:
            return self._fin(VerificationStatus.REJECTED, 0, None, None, asc,
                             ocr_fields, [f"FACE_ERR:{e}"], scores, client_ip)
        try:
            lr = self.liveness.check(selfie_bytes)
            ls = float(lr.get("score", 0))
            scores["liveness"] = ls
            if ls < self.lt:
                reasons.append(f"LIVE:{ls:.3f}")
        except Exception as e:
            return self._fin(VerificationStatus.REJECTED, 0, fs, None, asc,
                             ocr_fields, [f"LIVE_ERR:{e}"], scores, client_ip)
        if expected:
            for k, v in expected.items():
                if (ocr_fields.get(k) or "").strip().upper() != v.strip().upper():
                    reasons.append(f"FIELD:{k}")
        # AI Risk Engine
        # self.risk_engine already initialized
        _risk_result = self.risk_engine.compute(scores)
        _decision_result = self.decision_engine.decide(_risk_result, scores, list(reasons))
        st = self._map_decision(_decision_result.decision)
        conf = max(0.0, 1.0 - _risk_result.score)
        return self._fin(st, conf, fs, ls, asc, ocr_fields, reasons, scores, client_ip,
                         risk_result=_risk_result, decision_result=_decision_result)

    def _fin(self, st, conf, fs, ls, asc, ocr, reasons, scores, ip,
             risk_result=None, decision_result=None):
        r = VerificationResult(st, conf, fs, ls, asc, ocr, reasons, scores)
        try:
            from src.services.audit_db import AuditRecord
            r.audit_id = self.db.log(AuditRecord(
                None, time.time(), st.value, conf, fs, ls, asc, ocr, reasons, ip))
        except Exception as e:
            logger.warning(f"audit: {e}")

        # === AI report (decision يعكس st الحقيقي، لا placeholder) ===
        if risk_result is None:
            risk_result = self._fallback_risk("no_risk_result")
        if decision_result is None:
            from src.modules.ai.models import DecisionResult, Decision
            try:
                d = Decision(st.value)
            except ValueError:
                d = Decision.REJECTED
            decision_result = DecisionResult(
                decision=d, risk=risk_result,
                reasons=list(reasons or []), raw_scores=dict(scores or {}),
            )
        try:
            r.ai_report = self.report_builder.build(
                decision_result=decision_result,
                signals=scores or {},
            ).to_dict()
        except Exception as _e:
            logger.error(f"report_builder failed: {_e}")
            r.ai_report = {"error": str(_e)}
        return r

    @staticmethod
    def _fallback_risk(reason: str):
        """RiskScore احتياطي عندما لا يوجد risk_result.

        ملاحظة: components dict[float] فقط — نضع reason في model_version.
        """
        from src.modules.ai.models import RiskScore, RiskLevel
        return RiskScore(
            score=1.0,
            level=RiskLevel.CRITICAL,
            components={"error": 1.0},
            model_version=f"fallback:{reason}",
            threshold_version="fallback",
        )

    @staticmethod
    def _map_decision(d) -> "VerificationStatus":
        from src.modules.ai.models import Decision
        if d == Decision.VERIFIED:
            return VerificationStatus.VERIFIED
        if d == Decision.MANUAL_REVIEW:
            return VerificationStatus.MANUAL_REVIEW
        return VerificationStatus.REJECTED
