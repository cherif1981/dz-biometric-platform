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


class VerificationEngine:
    def __init__(self, ft=None, lt=None, ast=None):
        from src.core.config import settings
        ft = ft if ft is not None else settings.FACE_MATCH_THRESHOLD
        lt = lt if lt is not None else settings.LIVENESS_THRESHOLD
        ast = ast if ast is not None else getattr(settings, 'ANTISPOOF_THRESHOLD', 0.45)

        from src.services.face_service import FaceService
        from src.services.liveness_service import LivenessService
        from src.services.ocr_service import OCRService
        from src.services.antispoofing_service import AntiSpoofing
        from src.services.audit_db import AuditDB
        self.face = FaceService.get()
        # Phase 2: Document AI
        self.document_ai = DocumentAI(ocr_service=getattr(self, 'ocr', None))

        # Phase 3: Biometric AI

        self.biometric_ai = BiometricAI(face_app=getattr(self, 'face', None))


        # Phase 4: AI Report Builder


        self.report_builder = ReportBuilder()
        self.risk_engine = RiskEngine()
        self.decision_engine = DecisionEngine()

        self.liveness = LivenessService()
        self.ocr = OCRService()
        self.antispoof = AntiSpoofing(ast)
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
        conf = 1.0 - _risk_result.score
        if not reasons:
            st = VerificationStatus.VERIFIED
        elif (fs >= self.ft - self.band and ls >= self.lt - self.band
              and (asc or 0) >= self.ast - self.band and len(reasons) <= 1):
            st = VerificationStatus.MANUAL_REVIEW
        else:
            st = VerificationStatus.REJECTED
        return self._fin(st, conf, fs, ls, asc, ocr_fields, reasons, scores, client_ip)

    def _fin(self, st, conf, fs, ls, asc, ocr, reasons, scores, ip):
        r = VerificationResult(st, conf, fs, ls, asc, ocr, reasons, scores)
        try:
            from src.services.audit_db import AuditRecord

            r.audit_id = self.db.log(AuditRecord(
                None, time.time(), st.value, conf, fs, ls, asc, ocr, reasons, ip))
        except Exception as e:
            logger.warning(f"audit: {e}")
        # Phase 4: build unified AI report
        try:
            _ai_report = self.report_builder.build(
                decision_result=type('DR', (), {
                    'decision': VerificationStatus.VERIFIED,  # placeholder
                    'risk': _risk_result,
                    'reasons': reasons,
                    'raw_scores': scores,
                })(),
                signals=scores,
            ).to_dict()
        except Exception as _e:
            _ai_report = {'error': str(_e)}

        return r
