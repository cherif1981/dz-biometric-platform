import re
from typing import Dict, Optional

class FieldExtractor:
    NIN_PATTERN = re.compile(r"\b\d{18}\b")
    DATE_PATTERN = re.compile(r"\b\d{2}[/\-\.]\d{2}[/\-\.]\d{4}\b")

    def extract(self, text: str) -> Dict[str, Optional[str]]:
        return {
            "nin": self._extract_nin(text),
            "nom": self._extract_after(text, ["اللقب", "Nom"]),
            "prenom": self._extract_after(text, ["الاسم", "Prénom", "Prenom"]),
            "date_naissance": self._extract_date(text, index=0),
            "date_expiration": self._extract_date(text, index=-1),
            "lieu_naissance": self._extract_after(text, ["مكان الميلاد", "Lieu"]),
            "sexe": self._extract_sexe(text),
        }

    def _extract_nin(self, text):
        m = self.NIN_PATTERN.search(text)
        return m.group() if m else None

    def _extract_date(self, text, index):
        dates = self.DATE_PATTERN.findall(text)
        return dates[index] if dates else None

    def _extract_after(self, text, keywords):
        for kw in keywords:
            pattern = rf"{re.escape(kw)}[:\s]+([A-Za-z\u0600-\u06FF\s]{{2,40}})"
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return None

    def _extract_sexe(self, text):
        if re.search(r"\b(M|Masculin|ذكر)\b", text, re.IGNORECASE):
            return "M"
        if re.search(r"\b(F|Féminin|أنثى)\b", text, re.IGNORECASE):
            return "F"
        return None
