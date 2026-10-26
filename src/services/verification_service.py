from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any
from loguru import logger
import time

# === AI Risk Engine : import déplacé dans __init__ (lazy loading) ===
# L'import en haut du fichier chargeait cv2 via src.modules.ai,
# ce qui faisait échouer la collecte pytest si opencv n'était pas installé.
# from src.modules.ai import RiskEngine, DecisionEngine, DocumentAI, BiometricAI, ReportBuilder


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
        # === Imports lourds déplacés ici (lazy loading) ===
        from src.modules.ai import (
            RiskEngine,
            DecisionEngine,
            DocumentAI,
            BiometricAI,
            ReportBuilder,
        )
        from src.core.thresholds import get_thresholds
        from src.services.face_service import FaceVerificationService as FaceService
        from src.services.liveness_service import LivenessService
        from src.services.ocr_service import OCRService
        from src.services.antispoofing_service import AntiSpoofing
        from src.services.audit_db import AuditDB
        # === end ===

        _t = get_thresholds()
        ft = ft if ft is not None else _t.face_similarity
        lt = lt if lt is not None else _t.liveness
        ast = ast if ast is not None else _t.antispoofing

        self.face = FaceService.get()
        self.document_ai = DocumentAI(ocr_service=getattr(self, "ocr", None))
        self.biometric_ai = BiometricAI(face_app=getattr(self, "face", None))
        self.report_builder = ReportBuilder()
        self.risk_engine = RiskEngine()
        self.decision_engine = DecisionEngine()
        self.liveness = LivenessService()
        self.ocr = OCRService()
        self.antispoof = _make_antispoof(ast)
        self.db = AuditDB()
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
            return self._fin(
                VerificationStatus.REJECTED, 0, None, None, None,
                {}, [f"OCR_ERROR:{e}"], {}, client_ip,
            )

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
            return self._fin(
                VerificationStatus.REJECTED, 0, None, None, asc,
                ocr_fields, [f"FACE_ERR:{e}"], scores, client_ip,
            )

        try:
            lr = self.liveness.check(selfie_bytes)
            ls = float(lr.get("score", 0))
            scores["liveness"] = ls
            if ls < self.lt:
                reasons.append(f"LIVE:{ls:.3f}")
        except Exception as e:
            return self._fin(
                VerificationStatus.REJECTED, 0, fs, None, asc,
                ocr_fields, [f"LIVE_ERR:{e}"], scores, client_ip,
            )

        if expected:
            for k, v in expected.items():
                if (ocr_fields.get(k) or "").strip().upper() != v.strip().upper():
                    reasons.append(f"FIELD:{k}")

        _risk_result = self.risk_engine.compute(scores)
        conf = 1.0 - _risk_result.score

        if not reasons:
            st = VerificationStatus.VERIFIED
        elif (
            fs >= self.ft - self.band
            and ls >= self.lt - self.band
            and (asc or 0) >= self.ast - self.band
            and len(reasons) <= 1
        ):
            st = VerificationStatus.MANUAL_REVIEW
        else:
            st = VerificationStatus.REJECTED

        return self._fin(
            st, conf, fs, ls, asc, ocr_fields, reasons, scores, client_ip,
            risk_result=_risk_result,
        )

    def _fin(self, st, conf, fs, ls, asc, ocr, reasons, scores, ip, risk_result=None):
        r = VerificationResult(st, conf, fs, ls, asc, ocr, reasons, scores)

        try:
            from src.services.audit_db import AuditRecord
            r.audit_id = self.db.log(
                AuditRecord(
                    None, time.time(), st.value, conf, fs, ls, asc, ocr, reasons, ip
                )
            )
        except Exception as e:
            logger.warning(f"audit: {e}")

        # Phase 4: build unified AI report
        try:
            dr = type(
                "DR",
                (),
                {
                    "decision": st,
                    "risk": risk_result,
                    "reasons": reasons,
                    "raw_scores": scores,
                },
            )()
            r.ai_report = self.report_builder.build(
                decision_result=dr, signals=scores
            ).to_dict()
        except Exception as _e:
            r.ai_report = {"error": str(_e)}
            logger.warning(f"report_builder failed: {_e}")

        return r


# ═══════════════════════════════════════════════════════════════════
# مساعد إنشاء AntiSpoofing بأمان (مضاف في نهاية الملف)
# ═══════════════════════════════════════════════════════════════════
def _make_antispoof(cfg=None):
    """
    ينشئ AntiSpoofing مع استخراج العتبات من cfg بأمان.
    يدعم dict / object / None، ويعود للافتراضيات عند الفشل.
    """
    from src.services.antispoofing_service import AntiSpoofing

    def _get(name, default=None):
        if cfg is None:
            return default
        if isinstance(cfg, dict):
            return cfg.get(name, default)
        return getattr(cfg, name, default)

    reject = _get("threshold_reject")
    accept = _get("threshold_accept")
    if reject is None:
        reject = _get("antispoofing_threshold_reject")
    if accept is None:
        accept = _get("antispoofing_threshold_accept")

    try:
        reject = float(reject) if reject is not None else None
        accept = float(accept) if accept is not None else None
    except (TypeError, ValueError):
        reject = accept = None

    if reject is None or accept is None:
        return AntiSpoofing()
    return AntiSpoofing(threshold_reject=reject, threshold_accept=accept)
