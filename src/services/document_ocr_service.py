"""Document OCR service — Path B (input side) of KYC verification.

Extracts text + fields from identity documents (CNIBE, Algerian passport).
Independent from document authenticity validation (separate service).

Design principles:
- Never imports paddleocr/cv2 at module level (lazy load).
- Never makes a decision — outputs structured data only.
- Never validates MRZ checksums — that belongs to document_auth_service.
- One language failing does not block the other.
- Fail-closed on empty/invalid input.

Requires (runtime only, not for CI):
    pip install "paddleocr>=2.7,<3.0" paddlepaddle
"""
from __future__ import annotations

import re
from typing import Optional

import numpy as np


# ── Arabic-Indic digit normalization ─────────────────────────────────
_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


def normalize_arabic_digits(text: str) -> str:
    """Convert Arabic-Indic digits to ASCII digits."""
    if not text:
        return text
    return text.translate(_ARABIC_DIGITS)


# ── Label + value extraction helpers ─────────────────────────────────
def _first_match(patterns, text):
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE | re.MULTILINE)
        if m:
            return m.group(1).strip()
    return None


def _extract_nin(text):
    """Extract 18-digit NIN (allow spaces/dots as group separators)."""
    m = re.search(
        r"N\.?\s*I\.?\s*N\.?\s*[:\uFF1A]?\s*((?:\d[\s.]*){18})",
        text, re.IGNORECASE,
    )
    if m:
        digits = re.sub(r"\D", "", m.group(1))
        if len(digits) == 18:
            return digits
    m = re.search(r"(?<![0-9])((?:[0-9][\s.]*){18})(?![0-9])", text)
    if m:
        digits = re.sub(r"\D", "", m.group(1))
        if len(digits) == 18:
            return digits
    return None


# ── Field patterns ───────────────────────────────────────────────────
CNIBE_PATTERNS = {
    "surname": [
        r"(?:Nom|NOM|\u0627\u0644\u0627\u0633\u0645 \u0627\u0644\u0639\u0627\u0626\u0644\u064a)\s*[:\uFF1A]?\s*([A-Z\u0600-\u06FF][A-Za-z\u0600-\u06FF \t\-\u2019']{1,40})",
    ],
    "given_name": [
        r"(?:Pr[\u00E9e]nom|PR[\u00C9E]NOM|\u0627\u0644\u0627\u0633\u0645)\s*[:\uFF1A]?\s*([A-Z\u0600-\u06FF][A-Za-z\u0600-\u06FF \t\-\u2019']{1,40})",
    ],
    "dob": [
        r"(?:Date de naissance|DATE DE NAISSANCE|N[\u00E9e] le|\u062A\u0627\u0631\u064A\u062E \u0627\u0644\u0645\u064A\u0644\u0627\u062F)\s*[:\uFF1A]?\s*(\d{2}[/\-\.]\d{2}[/\-\.]\d{4})",
        r"\b(\d{2}[/\-\.]\d{2}[/\-\.]\d{4})\b",
    ],
    "place_of_birth": [
        r"(?:Lieu de naissance|LIEU DE NAISSANCE|\u0645\u0643\u0627\u0646 \u0627\u0644\u0645\u064A\u0644\u0627\u062F)\s*[:\uFF1A]?\s*([A-Z\u0600-\u06FF][A-Za-z\u0600-\u06FF \t\-\u2019']{1,40})",
    ],
    "sex": [
        r"(?:Sexe|SEXE|\u0627\u0644\u062C\u0646\u0633)\s*[:\uFF1A]?\s*(M|F|Masculin|F[\u00E9e]minin|\u0630\u0643\u0631|\u0623\u0646\u062B\u0649)",
    ],
}

PASSPORT_PATTERNS = {
    "passport_no": [
        r"(?:Passeport\s*No|Passport\s*No|N[\u00B0o]\s*de\s*passeport)\s*[:\uFF1A]?\s*([A-Z]{1,2}\d{6,8})",
        r"\b([A-Z]{2}\d{7})\b",
    ],
    "surname": [
        r"(?:Nom|Surname|\u0627\u0644\u0644\u0642\u0628)\s*[:\uFF1A]?\s*([A-Z\u0600-\u06FF][A-Za-z\u0600-\u06FF \t\-\u2019']{1,30})",
    ],
    "given_name": [
        r"(?:Pr[\u00E9e]nom|Given name|\u0627\u0644\u0627\u0633\u0645)\s*[:\uFF1A]?\s*([A-Z\u0600-\u06FF][A-Za-z\u0600-\u06FF \t\-\u2019']{1,30})",
    ],
    "dob": [
        r"(?:Date de naissance|Date of birth|\u062A\u0627\u0631\u064A\u062E \u0627\u0644\u0645\u064A\u0644\u0627\u062F)\s*[:\uFF1A]?\s*(\d{2}[/\-\.]\d{2}[/\-\.]\d{4})",
    ],
    "expiry": [
        r"(?:Date d.expiration|Date of expiry|Expiry)\s*[:\uFF1A]?\s*(\d{2}[/\-\.]\d{2}[/\-\.]\d{4})",
    ],
}


# ── Pure parsers (testable without any model) ────────────────────────
def parse_cnibe_fields(text: str) -> dict:
    text = normalize_arabic_digits(text or "")
    fields = {k: _first_match(pats, text) for k, pats in CNIBE_PATTERNS.items()}
    fields["nin"] = _extract_nin(text)
    return fields


def parse_passport_fields(text: str) -> dict:
    text = normalize_arabic_digits(text or "")
    return {k: _first_match(pats, text) for k, pats in PASSPORT_PATTERNS.items()}


_MRZ_LINE_RE = re.compile(r"^[A-Z0-9<]{44}$")


def detect_document_type_from_text(text: str) -> str:
    if not text:
        return "unknown"
    normalized = normalize_arabic_digits(text).upper()
    lines = [l.strip() for l in normalized.splitlines()]
    mrz_lines = [l for l in lines if _MRZ_LINE_RE.match(l)]
    if len(mrz_lines) >= 2:
        return "passport"
    if any(kw in normalized for kw in ("N.I.N", "NIN", "CARTE NATIONALE")):
        return "cnibe"
    if any(kw in normalized for kw in ("PASSEPORT", "PASSPORT")):
        return "passport"
    return "unknown"


# ── Service class ────────────────────────────────────────────────────
class DocumentOCRService:
    """Lazy-loaded multi-language OCR extractor.

    PaddleOCR instances are created per language on first use.
    Failures in one language do not raise — the other still runs.
    """

    def __init__(self, langs: tuple = ("ar", "fr")):
        self._langs = langs
        self._ocr_instances: dict = {}

    def _get_ocr(self, lang: str):
        if lang in self._ocr_instances:
            return self._ocr_instances[lang]
        try:
            from paddleocr import PaddleOCR
        except ImportError as e:
            raise ImportError(
                "PaddleOCR not installed. Run:\n"
                '  pip install "paddleocr>=2.7,<3.0" paddlepaddle'
            ) from e
        ocr = PaddleOCR(use_angle_cls=True, lang=lang, show_log=False)
        self._ocr_instances[lang] = ocr
        return ocr

    def _ocr_lang(self, image_bgr: np.ndarray, lang: str) -> list:
        ocr = self._get_ocr(lang)
        result = ocr.ocr(image_bgr, cls=True)
        if not result or result[0] is None:
            return []
        return [
            {"text": line[1][0], "confidence": float(line[1][1]), "bbox": line[0]}
            for line in result[0]
            if line and len(line) >= 2
        ]

    def extract_raw_text(self, image_bgr: np.ndarray) -> list:
        """Run OCR for each language; merge lines; drop per-lang failures."""
        if image_bgr is None or getattr(image_bgr, "size", 0) == 0:
            raise ValueError("empty image")
        lines = []
        for lang in self._langs:
            try:
                lines.extend(self._ocr_lang(image_bgr, lang))
            except Exception:
                continue
        return lines

    def extract_text_string(self, image_bgr: np.ndarray) -> str:
        return "\n".join(item["text"] for item in self.extract_raw_text(image_bgr))

    def extract_fields(self, image_bgr: np.ndarray,
                       doc_type: Optional[str] = None) -> dict:
        text = self.extract_text_string(image_bgr)
        if doc_type is None:
            doc_type = detect_document_type_from_text(text)
        if doc_type == "cnibe":
            fields = parse_cnibe_fields(text)
        elif doc_type == "passport":
            fields = parse_passport_fields(text)
        else:
            fields = {}
        return {
            "doc_type": doc_type,
            "fields": fields,
            "raw_text": text,
            "raw_lines": self.extract_raw_text(image_bgr),
        }


_service: Optional[DocumentOCRService] = None


def get_document_ocr_service() -> DocumentOCRService:
    global _service
    if _service is None:
        _service = DocumentOCRService()
    return _service
