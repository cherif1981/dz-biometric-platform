"""
مستخرج حقول مخصص للبطاقة البيومترية الجزائرية
يدعم العربية والفرنسية
"""
import re
from typing import Dict, Optional, List


class DZFieldExtractor:
    """مستخرج حقول البطاقة البيومترية الجزائرية"""

    # ============ الأنماط ============
    NIN_PATTERN = re.compile(r"\b\d{18}\b")
    DATE_PATTERN = re.compile(r"\b\d{2}[/\-\.]\d{2}[/\-\.]\d{4}\b")

    # ============ الكلمات المفتاحية ============
    KEYWORDS = {
        "nom": [
            "اللقب", "لقب", "Nom", "NOM", "Nom de famille",
        ],
        "prenom": [
            "الاسم", "اسم", "Prénom", "Prenom", "PRENOM",
            "Prénoms", "Prenoms",
        ],
        "date_naissance": [
            "تاريخ الميلاد", "الميلاد", "Né le", "Née le",
            "Date de naissance", "Naissance",
        ],
        "lieu_naissance": [
            "مكان الميلاد", "Lieu de naissance", "Lieu",
        ],
        "date_expiration": [
            "صالحة إلى", "صالحة حتى", "Valable jusqu'au",
            "Expire le", "Date d'expiration", "Expiration",
        ],
        "sexe": [
            "الجنس", "Sexe", "Sex",
        ],
        "nin": [
            "رقم التعريف", "رقم التعريف الوطني", "NIN",
            "N.I.N", "Identifiant",
        ],
        "adresse": [
            "العنوان", "Adresse",
        ],
    }

    # ============ أنماط الأسماء ============
    ARABIC_WORD = re.compile(r"[\u0600-\u06FF]{2,}")
    LATIN_WORD = re.compile(r"[A-Za-zÀ-ÿ]{2,}")

    # ============ كلمات يجب تجاهلها ============
    STOPWORDS = {
        "الجمهورية", "الجزائرية", "الديمقراطية", "الشعبية",
        "بطاقة", "التعريف", "الوطنية", "البيومترية",
        "République", "Algérienne", "Démocratique", "Populaire",
        "Carte", "Nationale", "Biométrique", "Identité",
    }

    def extract(self, text: str) -> Dict[str, Optional[str]]:
        """استخراج كل الحقول من النص"""
        text = self._normalize(text)

        # استخراج أولي
        result = {
            "nin": self._extract_nin(text),
            "nom": self._extract_field(text, "nom"),
            "prenom": self._extract_field(text, "prenom"),
            "date_naissance": self._extract_date_by_keyword(text, "date_naissance"),
            "date_expiration": self._extract_date_by_keyword(text, "date_expiration"),
            "lieu_naissance": self._extract_field(text, "lieu_naissance"),
            "sexe": self._extract_sexe(text),
        }

        # إذا لم نجد التاريخ بالكلمة المفتاحية، جرب جميع التواريخ
        if not result["date_naissance"] and not result["date_expiration"]:
            dates = self.DATE_PATTERN.findall(text)
            if dates:
                result["date_naissance"] = dates[0]
                if len(dates) > 1:
                    result["date_expiration"] = dates[-1]

        # إذا لم نجد NIN، جرب استخراج 18 رقماً من النص بعد التنظيف
        if not result["nin"]:
            digits = re.sub(r"\D", "", text)
            m = re.search(r"\d{18}", digits)
            if m:
                result["nin"] = m.group()

        # إذا لم نجد الاسم/اللقب، حاول استخراج الأسماء العربية/اللاتينية
        if not result["nom"]:
            result["nom"] = self._fallback_name(text, "nom")
        if not result["prenom"]:
            result["prenom"] = self._fallback_name(text, "prenom")

        return result

    # ============ التطبيع ============
    def _normalize(self, text: str) -> str:
        """تنظيف وتوحيد النص"""
        # توحيد المسافات
        text = re.sub(r"\s+", " ", text)
        # تصحيح أخطاء OCR الشائعة
        replacements = {
            "N0M": "NOM",
            "NlN": "NIN",
            "N1N": "NIN",
            "Pr6nom": "Prenom",
            "Pren0m": "Prenom",
            "Nom :": "Nom:",
            "Prénom :": "Prénom:",
        }
        for wrong, right in replacements.items():
            text = text.replace(wrong, right)
        return text.strip()

    # ============ NIN ============
    def _extract_nin(self, text: str) -> Optional[str]:
        """استخراج رقم التعريف الوطني (18 رقماً)"""
        m = self.NIN_PATTERN.search(text)
        return m.group() if m else None

    # ============ الحقول النصية ============
    def _extract_field(self, text: str, field: str) -> Optional[str]:
        """استخراج حقل بناءً على الكلمات المفتاحية"""
        keywords = self.KEYWORDS.get(field, [])

        for kw in keywords:
            # نمط: كلمة مفتاحية + فاصل + قيمة
            pattern = rf"{re.escape(kw)}\s*[:\-]?\s*([^\n]{{2,60}})"
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                value = m.group(1).strip()
                value = self._clean_value(value)
                if self._is_valid_name(value):
                    return value
        return None

    def _clean_value(self, value: str) -> str:
        """تنظيف القيمة المستخرجة"""
        # إزالة الكلمات المفتاحية الأخرى من النهاية
        for kws in self.KEYWORDS.values():
            for kw in kws:
                # إزالة فقط إذا ظهرت في النهاية
                value = re.sub(rf"\s*{re.escape(kw)}\s*$", "", value)

        # إزالة الرموز الزائدة
        value = re.sub(r"[:\-\.\,،]+", " ", value)
        value = re.sub(r"\s+", " ", value).strip()

        # إزالة الأرقام الطويلة (NIN، تواريخ)
        value = re.sub(r"\b\d{6,}\b", "", value).strip()

        # إزالة التواريخ
        value = self.DATE_PATTERN.sub("", value).strip()

        return value

    def _is_valid_name(self, value: str) -> bool:
        """التحقق من أن القيمة اسم صالح"""
        if not value or len(value) < 2 or len(value) > 60:
            return False

        # يجب أن يحتوي على حرف واحد على الأقل
        if not (self.ARABIC_WORD.search(value) or self.LATIN_WORD.search(value)):
            return False

        # تجاهل الكلمات الشائعة
        for stop in self.STOPWORDS:
            if stop in value:
                return False

        # تجاهل إذا كانت كلها أرقام
        if value.replace(" ", "").isdigit():
            return False

        return True

    # ============ التواريخ ============
    def _extract_date_by_keyword(self, text: str, field: str) -> Optional[str]:
        """استخراج تاريخ مرتبط بكلمة مفتاحية"""
        keywords = self.KEYWORDS.get(field, [])

        for kw in keywords:
            # نمط: كلمة مفتاحية ثم أي شيء ثم تاريخ
            pattern = rf"{re.escape(kw)}[^\d]{{0,50}}(\d{{2}}[/\-\.]\d{{2}}[/\-\.]\d{{4}})"
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                return m.group(1)
        return None

    # ============ الجنس ============
    def _extract_sexe(self, text: str) -> Optional[str]:
        """استخراج الجنس"""
        # ذكر / Masculin / M
        if re.search(r"\b(Masculin|ذكر|Homme)\b", text, re.IGNORECASE):
            return "M"
        if re.search(r"\b(Féminin|Feminin|أنثى|Femme)\b", text, re.IGNORECASE):
            return "F"
        # رمز واحد مع حدود
        if re.search(r"\bM\b", text):
            return "M"
        if re.search(r"\bF\b", text):
            return "F"
        return None

    # ============ احتياطي للأسماء ============
    def _fallback_name(self, text: str, field: str) -> Optional[str]:
        """محاولة استخراج اسم من النص بدون كلمة مفتاحية"""
        # البحث عن سلاسل عربية
        if field == "nom":
            # الاسم الأول في القائمة بعد تجاهل stopwords
            candidates = self.ARABIC_WORD.findall(text)
        else:
            candidates = self.ARABIC_WORD.findall(text)

        for cand in candidates:
            if cand in self.STOPWORDS:
                continue
            if 2 <= len(cand) <= 30:
                return cand
        return None
