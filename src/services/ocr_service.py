"""
Enhanced OCR service with:
- MRZ parsing (ICAO 9303 TD1 format for Algerian ID)
- Structured field extraction
- Human review flag for low-confidence results
"""

import re

import cv2
import numpy as np
from loguru import logger

try:
    import easyocr

    HAS_EASYOCR = True
except ImportError:
    HAS_EASYOCR = False
    logger.warning("EasyOCR not installed — OCR disabled")


class OCRService:
    def __init__(self, *args, **kwargs):
        pass

    _readers = None
    REVIEW_THRESHOLD = 0.65

    @classmethod
    def _get(cls):
        if not HAS_EASYOCR:
            return None
        if cls._readers is None:
            cls._readers = (
                easyocr.Reader(["ar"], gpu=False, verbose=False),
                easyocr.Reader(["fr", "en"], gpu=False, verbose=False),
            )
        return cls._readers

    def _parse_mrz(self, text):
        """Parse MRZ TD1 format (3 lines x 30 chars) for Algerian IDs."""
        fields = {}
        mrz_candidates = re.findall(r"[A-Z0-9<]{25,}", text)
        if not mrz_candidates:
            return fields

        for line in mrz_candidates:
            m = re.match(r"^([A-Z0-9<]{6})(\d{6})(\d)([MF<])(\d{6})", line)
            if m:
                dob_str = m.group(2)
                try:
                    yy = int(dob_str[0:2])
                    year = 1900 + yy if yy > 30 else 2000 + yy
                    fields["birth_date"] = f"{year}-{dob_str[2:4]}-{dob_str[4:6]}"
                    fields["sex"] = "M" if m.group(4) == "M" else "F"
                except Exception:
                    pass

            nin = re.search(r"\b(\d{18})\b", line)
            if nin:
                fields["nin"] = nin.group(1)

        return fields

    def extract(self, image_bytes):
        if not HAS_EASYOCR:
            return {
                "fields": {"raw_text": "stub"},
                "confidence": 0.0,
                "needs_human_review": True,
                "note": "easyocr not installed",
            }

        img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            return {
                "fields": {},
                "confidence": 0.0,
                "needs_human_review": True,
                "error": "decode_failed",
            }

        items = []
        for r in self._get():
            for _, t, c in r.readtext(img):
                items.append((t.strip(), float(c)))

        joined = " ".join(t for t, _ in items)
        fields = {"raw_text": joined[:2000]}

        nin = re.search(r"\b(\d{18})\b", joined)
        if nin:
            fields["nin"] = nin.group(1)

        date = re.search(r"\b(\d{2}[/.\-]\d{2}[/.\-]\d{4})\b", joined)
        if date:
            fields["birth_date"] = date.group(1)

        mrz_fields = self._parse_mrz(joined)
        fields.update(mrz_fields)

        conf = float(np.mean([c for _, c in items])) if items else 0.0

        needs_review = conf < self.REVIEW_THRESHOLD or "nin" not in fields or not items

        return {
            "fields": fields,
            "confidence": round(conf, 4),
            "needs_human_review": needs_review,
            "review_reason": (
                "low_confidence"
                if conf < self.REVIEW_THRESHOLD
                else "missing_nin"
                if "nin" not in fields
                else "no_text_detected"
                if not items
                else None
            ),
            "items": items[:20],
        }
