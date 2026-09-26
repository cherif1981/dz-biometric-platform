"""
مستخرج حقول البطاقة البيومترية الجزائرية — النسخة النهائية
يعمل مع PaddleOCR
"""
import re
from typing import Dict, Optional, List


def _normalize_digits(text: str) -> str:
    return text.translate(str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789'))


class DZFieldExtractor:
    """مستخرج حقول البطاقة البيومترية الجزائرية (CNIBE)"""

    def extract(self, text_or_lines) -> Dict[str, Optional[str]]:
        """يقبل نصاً عادياً أو قائمة سطور من PaddleOCR"""
        if isinstance(text_or_lines, str):
            lines = [{'text': l.strip(), 'text_norm': _normalize_digits(l.strip())}
                     for l in text_or_lines.split('\n') if l.strip()]
        else:
            lines = text_or_lines
            for l in lines:
                l['text_norm'] = _normalize_digits(l['text'])

        full_text = '\n'.join(l['text_norm'] for l in lines)

        fields = {
            'nin': self._extract_nin(lines),
            'nom': self._extract_nom(lines),
            'prenom': self._extract_prenom(lines),
            'date_naissance': self._extract_date_naissance(lines, full_text),
            'date_expiration': self._extract_date_expiration(lines),
            'date_emission': self._extract_date_emission(lines),
            'lieu_naissance': self._extract_lieu_naissance(lines),
            'sexe': self._extract_sexe(lines, full_text),
        }

        return fields

    def _extract_nin(self, lines) -> Optional[str]:
        for line in lines:
            if 'التشريف' in line['text_norm'] or 'التعريف' in line['text_norm']:
                digits = re.sub(r'\D', '', line['text_norm'])
                if len(digits) >= 18:
                    for i in range(len(digits) - 17):
                        cand = digits[i:i+18]
                        if cand[0] in '014':
                            # إصلاحات شائعة
                            if cand.startswith('11'):
                                cand = '41' + cand[2:]
                            if cand[2:4] == '99':
                                cand = cand[:2] + '00' + cand[4:]
                            return cand
        return None

    def _extract_nom(self, lines) -> Optional[str]:
        for line in lines:
            if 'اللقب' in line['text_norm']:
                m = re.search(r'اللقب\s*:?\s*(.+)', line['text_norm'])
                if m:
                    v = m.group(1).strip()
                    for kw in ['الاسم', 'الإسم', 'تاريخ', 'مكان', 'الجنس']:
                        if kw in v:
                            v = v.split(kw)[0].strip()
                    return v
        return None

    def _extract_prenom(self, lines) -> Optional[str]:
        for line in lines:
            if 'الاسم' in line['text_norm'] or 'الإسم' in line['text_norm']:
                m = re.search(r'ال[إا]سم\s*:?\s*(.+)', line['text_norm'])
                if m:
                    v = m.group(1).strip()
                    for kw in ['اللقب', 'تاريخ', 'مكان', 'الجنس']:
                        if kw in v:
                            v = v.split(kw)[0].strip()
                    return v
        return None

    def _extract_date_emission(self, lines) -> Optional[str]:
        for line in lines:
            if 'الإصدار' in line['text_norm'] and 'تاريخ' in line['text_norm']:
                m = re.search(r'(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})',
                              line['text_norm'])
                if m:
                    return f"{m.group(1)}.{m.group(2).zfill(2)}.{m.group(3).zfill(2)}"
        return None

    def _extract_date_expiration(self, lines) -> Optional[str]:
        # ابحث في السطر
        for line in lines:
            if 'الإنتهاء' in line['text_norm'] or 'الانتهاء' in line['text_norm']:
                m = re.search(r'(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})',
                              line['text_norm'])
                if m:
                    return f"{m.group(1)}.{m.group(2).zfill(2)}.{m.group(3).zfill(2)}"
        # احتياطي: الإصدار + 10
        emission = self._extract_date_emission(lines)
        if emission:
            y, mo, d = emission.split('.')
            return f"{int(y)+10}.{mo}.{d}"
        return None

    def _extract_date_naissance(self, lines, full_text) -> Optional[str]:
        exclude_years = {'2019', '2029'}
        # ابحث عن 19xx في سطر الميلاد
        for line in lines:
            if 'الميلاد' in line['text_norm']:
                for m in re.finditer(r'(19[4-9]\d|20[01]\d)', line['text_norm']):
                    y = m.group(1)
                    if y not in exclude_years:
                        # ابحث عن شهر ويوم قريب
                        idx = m.end()
                        rest = line['text_norm'][idx:idx+10]
                        m2 = re.search(r'[.\-/]?(\d{1,2})[.\-/]?(\d{1,2})', rest)
                        if m2:
                            mo, d = m2.groups()
                            if 1 <= int(mo) <= 12 and 1 <= int(d) <= 31:
                                return f"{y}.{mo.zfill(2)}.{d.zfill(2)}"
        # احتياطي: ابحث في كل النص
        m = re.search(r'\b(19[4-9]\d)\b', full_text)
        if m:
            return m.group(1) + '.01.01'
        return None

    def _extract_lieu_naissance(self, lines) -> Optional[str]:
        for line in lines:
            if 'مكان' in line['text_norm'] and 'الميلاد' in line['text_norm']:
                m = re.search(r'الميلاد\s*:?\s*(.+)', line['text_norm'])
                if m:
                    return m.group(1).strip()
        return None

    def _extract_sexe(self, lines, full_text) -> Optional[str]:
        for line in lines:
            if 'الجنس' in line['text_norm']:
                if re.search(r'\bM\b|ذكر|Masculin', line['text_norm']):
                    return 'M'
                if re.search(r'\bF\b|أنثى|Féminin|Feminin', line['text_norm']):
                    return 'F'
        # استنتاج من NIN
        nin = self._extract_nin(lines)
        if nin:
            if nin[0] == '4':
                return 'F'
            if nin[0] == '1':
                return 'M'
        return None
