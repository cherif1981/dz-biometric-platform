"""Document authenticity service — Path B (security side) of KYC.

Validates MRZ checksums (ICAO 9303) and provides a recapture-liveness
interface. Consumes OCR output; does NOT make identity decisions.

Independence contract:
- This module NEVER imports face matching or PAD decision logic.
- Output is evidence, not a verdict. The orchestrator combines evidence.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Optional


# ═══════════════════════════════════════════════════════════════════════
# ICAO 9303 MRZ — checksum + validation
# ═══════════════════════════════════════════════════════════════════════
# Weights for each field position (ICAO 9303, Part 3, Section 4.9)
_WEIGHTS = (7, 3, 1)


def _char_value(ch: str) -> int:
    """MRZ character value: digits = 0-9, A-Z = 10-35, '<' = 0."""
    if ch.isdigit():
        return int(ch)
    if "A" <= ch <= "Z":
        return ord(ch) - ord("A") + 10
    if ch == "<":
        return 0
    raise ValueError(f"invalid MRZ character: {ch!r}")


def mrz_checksum(field: str) -> int:
    """Compute the MRZ check digit for a field."""
    total = 0
    for i, ch in enumerate(field):
        total += _char_value(ch) * _WEIGHTS[i % 3]
    return total % 10


# ── TD3 (passport) ────────────────────────────────────────────────────
@dataclass
class TD3Result:
    valid: bool
    checksums: dict = field(default_factory=dict)
    fields: dict = field(default_factory=dict)
    errors: list = field(default_factory=list)


def validate_td3_mrz(line2: str) -> TD3Result:
    """Validate TD3 (passport) line 2 checksums.

    Line 2 layout (44 chars):
      [0:9]   passport number + check [9]
      [10:13] nationality
      [13:19] DOB YYMMDD + check [19]
      [20]    sex
      [21:27] expiry YYMMDD + check [27]
      [28:42] personal number + check [42]
      [43]    composite check
    """
    result = TD3Result(valid=False)

    if len(line2) != 44:
        result.errors.append(f"line2 length {len(line2)} != 44")
        return result

    try:
        # Individual checksums
        doc_no_field, doc_no_check = line2[0:9], int(line2[9])
        dob_field, dob_check = line2[13:19], int(line2[19])
        exp_field, exp_check = line2[21:27], int(line2[27])
        pers_field, pers_check = line2[28:42], int(line2[42])

        # Composite: doc_no + check + dob + check + exp + check + pers + check
        comp_field = (line2[0:10] + line2[13:20] + line2[21:28]
                      + line2[28:43])
        comp_check = int(line2[43])

        checks = {
            "doc_no": (mrz_checksum(doc_no_field), doc_no_check),
            "dob":    (mrz_checksum(dob_field),    dob_check),
            "expiry": (mrz_checksum(exp_field),    exp_check),
            "personal": (mrz_checksum(pers_field), pers_check),
            "composite": (mrz_checksum(comp_field), comp_check),
        }

        for name, (calc, actual) in checks.items():
            result.checksums[name] = {"calculated": calc, "present": actual,
                                      "ok": calc == actual}
            if calc != actual:
                result.errors.append(f"{name}_checksum_mismatch")

        result.fields = {
            "document_number": doc_no_field.replace("<", "").strip(),
            "date_of_birth":   dob_field,
            "date_of_expiry":  exp_field,
            "sex":             line2[20],
            "nationality":     line2[10:13],
            "personal_number": pers_field.replace("<", "").strip(),
        }
        result.valid = not result.errors
    except (ValueError, IndexError) as e:
        result.errors.append(f"parse_error: {e}")

    return result


# ── TD1 (ID card) ─────────────────────────────────────────────────────
@dataclass
class TD1Result:
    valid: bool
    checksums: dict = field(default_factory=dict)
    fields: dict = field(default_factory=dict)
    errors: list = field(default_factory=list)


def validate_td1_mrz(line1: str, line2: str) -> TD1Result:
    """Validate TD1 (ID card) lines 1+2 checksums. Both 30 chars.

    Line 1 (30):
      [0:5]   doc code (e.g., ID)
      [5:14]  doc number + check [14]
      [15:30] optional data 1
    Line 2 (30):
      [0:6]   DOB YYMMDD + check [6]
      [7]     sex
      [8:14]  expiry YYMMDD + check [14]
      [15:18] nationality
      [18:29] optional data 2 + check [29]
    """
    result = TD1Result(valid=False)
    if len(line1) != 30 or len(line2) != 30:
        result.errors.append(f"line lengths {len(line1)}/{len(line2)} != 30/30")
        return result

    try:
        doc_no_field, doc_no_check = line1[5:14], int(line1[14])
        dob_field, dob_check = line2[0:6], int(line2[6])
        exp_field, exp_check = line2[8:14], int(line2[14])
        opt2_field, opt2_check = line2[18:29], int(line2[29])

        checks = {
            "doc_no": (mrz_checksum(doc_no_field), doc_no_check),
            "dob":    (mrz_checksum(dob_field),    dob_check),
            "expiry": (mrz_checksum(exp_field),    exp_check),
            "opt2":   (mrz_checksum(opt2_field),   opt2_check),
        }
        for name, (calc, actual) in checks.items():
            result.checksums[name] = {"calculated": calc, "present": actual,
                                      "ok": calc == actual}
            if calc != actual:
                result.errors.append(f"{name}_checksum_mismatch")

        result.fields = {
            "document_number": doc_no_field.replace("<", "").strip(),
            "date_of_birth":   dob_field,
            "date_of_expiry":  exp_field,
            "sex":             line2[7],
            "nationality":     line2[15:18],
        }
        result.valid = not result.errors
    except (ValueError, IndexError) as e:
        result.errors.append(f"parse_error: {e}")

    return result


# ═══════════════════════════════════════════════════════════════════════
# MRZ line detection from raw OCR text
# ═══════════════════════════════════════════════════════════════════════
_MRZ_LINE_RE = re.compile(r"^[A-Z0-9<]{30,44}$")


def find_mrz_lines(raw_text: str) -> list:
    """Return MRZ-looking lines (uppercase A-Z/0-9/<, length 30-44)."""
    if not raw_text:
        return []
    lines = []
    for line in raw_text.splitlines():
        cleaned = line.strip().replace(" ", "")
        if _MRZ_LINE_RE.match(cleaned):
            lines.append(cleaned)
    return lines


# ═══════════════════════════════════════════════════════════════════════
# Recapture liveness interface (pluggable, no heavy model)
# ═══════════════════════════════════════════════════════════════════════
class RecaptureDetector:
    """Pluggable interface for document liveness.

    Default implementation returns 0.0 (never trust, fail-closed).
    Replace by injecting a real model later:

        detector = RecaptureDetector()
        detector.set_predictor(my_dlc2021_model.predict)
    """

    def __init__(self):
        self._predictor = None

    def set_predictor(self, fn):
        self._predictor = fn

    def predict(self, image_or_frames) -> float:
        if self._predictor is None:
            return 0.0  # fail-closed: no model → no liveness
        try:
            score = float(self._predictor(image_or_frames))
            return max(0.0, min(1.0, score))
        except Exception:
            return 0.0


# ═══════════════════════════════════════════════════════════════════════
# Service
# ═══════════════════════════════════════════════════════════════════════
@dataclass
class AuthResult:
    document_authentic: bool
    mrz_valid: bool
    liveness_score: float
    doc_type: str
    reasons: list = field(default_factory=list)
    mrz_fields: dict = field(default_factory=dict)


class DocumentAuthService:
    def __init__(self, recapture_detector: Optional[RecaptureDetector] = None,
                 liveness_threshold: float = 0.5):
        self.recapture = recapture_detector or RecaptureDetector()
        self.liveness_threshold = liveness_threshold

    def validate(self, raw_text: str, image_or_frames=None,
                 doc_type_hint: Optional[str] = None) -> AuthResult:
        reasons = []
        mrz_lines = find_mrz_lines(raw_text or "")

        mrz_valid = False
        mrz_fields = {}

        # Try TD3 (passport): 2 lines of 44
        td3_lines = [l for l in mrz_lines if len(l) == 44]
        if len(td3_lines) >= 2:
            r = validate_td3_mrz(td3_lines[-1])  # line 2 is last
            mrz_valid = r.valid
            mrz_fields = r.fields
            if not r.valid:
                reasons.extend(r.errors)
            doc_type = "passport"
        # Try TD1 (ID card): 3 lines of 30
        elif len(mrz_lines) >= 3 and all(len(l) == 30 for l in mrz_lines[:3]):
            r = validate_td1_mrz(mrz_lines[0], mrz_lines[1])
            mrz_valid = r.valid
            mrz_fields = r.fields
            if not r.valid:
                reasons.extend(r.errors)
            doc_type = "cnibe"
        else:
            doc_type = doc_type_hint or "unknown"
            reasons.append("no_mrz_found" if not mrz_lines else "mrz_layout_unknown")

        liveness = self.recapture.predict(image_or_frames) if image_or_frames is not None else 0.0
        if liveness < self.liveness_threshold:
            reasons.append("document_not_live")

        authentic = mrz_valid and (liveness >= self.liveness_threshold)

        return AuthResult(
            document_authentic=authentic,
            mrz_valid=mrz_valid,
            liveness_score=liveness,
            doc_type=doc_type,
            reasons=reasons,
            mrz_fields=mrz_fields,
        )


_service: Optional[DocumentAuthService] = None

def get_document_auth_service() -> DocumentAuthService:
    global _service
    if _service is None:
        _service = DocumentAuthService()
    return _service
