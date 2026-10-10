import re
from src.modules.ocr.arabic_engine import ArabicEngine
from src.modules.ocr.french_engine import FrenchEngine

# Simple regex-based field extraction. Extend with MRZ parser for passports.
_PATTERNS = {
    "nin": re.compile(r"\b\d{18}\b"),                       # Numéro d'Identification National
    "date": re.compile(r"\b\d{2}[./-]\d{2}[./-]\d{4}\b"),
    "name_latin": re.compile(r"[A-Z][A-Z\s]{3,}"),
}


def extract_fields(image, doc_type: str) -> tuple[dict, float]:
    ar = ArabicEngine().read(image)
    fr = FrenchEngine().read(image)

    combined = (fr["text"] or "") + "\n" + (ar["text"] or "")
    fields: dict = {"raw_text": combined, "doc_type": doc_type}

    m = _PATTERNS["nin"].search(combined.replace(" ", ""))
    if m:
        fields["nin"] = m.group()
    dates = _PATTERNS["date"].findall(combined)
    if dates:
        fields["dates"] = dates[:3]

    # MRZ lines for passports
    mrz = [ln for ln in combined.splitlines() if re.match(r"^[A-Z0-9<]{30,44}$", ln.strip())]
    if mrz:
        fields["mrz"] = mrz

    conf = (ar["confidence"] + fr["confidence"]) / 2
    return fields, conf