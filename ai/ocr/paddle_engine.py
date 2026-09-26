"""
PaddleOCR Engine — بديل Tesseract للبطاقات الجزائرية
دقة أعلى بكثير في العربية
"""
import re
from typing import Dict, List
import numpy as np


class PaddleOCREngine:
    """محرك OCR يعتمد على PaddleOCR"""

    def __init__(self):
        self._ocr = None

    @property
    def ocr(self):
        if self._ocr is None:
            from paddleocr import PaddleOCR
            self._ocr = PaddleOCR(use_angle_cls=True, lang='ar', show_log=False)
        return self._ocr

    @staticmethod
    def _fix_arabic(text: str) -> str:
        """يعكس النص العربي المكتوب بالعكس"""
        arabic_chars = len(re.findall(r'[\u0600-\u06FF]', text))
        total = len([c for c in text if c.strip()])
        if total == 0:
            return text
        if arabic_chars / total > 0.5:
            words = text.split()
            fixed = [w[::-1] if re.search(r'[\u0600-\u06FF]', w) else w
                     for w in words]
            return ' '.join(fixed[::-1])
        return text

    def _group_into_lines(self, result, y_tolerance=15) -> List[Dict]:
        """دمج الكلمات في صفوف أفقية"""
        if not result or not result[0]:
            return []

        items = []
        for line in result[0]:
            bbox, (text, conf) = line
            y_center = sum(p[1] for p in bbox) / 4
            x_left = min(p[0] for p in bbox)
            x_right = max(p[0] for p in bbox)
            items.append({
                'text': self._fix_arabic(text),
                'conf': conf,
                'y': y_center,
                'x_left': x_left,
                'x_right': x_right,
            })

        items.sort(key=lambda i: i['y'])

        lines = []
        current = [items[0]]
        for item in items[1:]:
            if abs(item['y'] - current[-1]['y']) <= y_tolerance:
                current.append(item)
            else:
                lines.append(current)
                current = [item]
        if current:
            lines.append(current)

        result_lines = []
        for line_items in lines:
            line_items.sort(key=lambda i: -i['x_right'])
            texts = [item['text'] for item in line_items]
            merged = ' '.join(texts)
            avg_conf = sum(item['conf'] for item in line_items) / len(line_items)
            result_lines.append({
                'text': merged,
                'y': line_items[0]['y'],
                'conf': avg_conf,
            })

        return result_lines

    def extract(self, image: np.ndarray) -> Dict:
        """استخراج النص — واجهة متوافقة مع OCREngine"""
        result = self.ocr.ocr(image, cls=True)
        lines = self._group_into_lines(result)

        full_text = '\n'.join(l['text'] for l in lines)
        confs = [l['conf'] for l in lines]
        avg_conf = sum(confs) / len(confs) * 100 if confs else 0.0

        return {
            "text": full_text,
            "confidence": round(avg_conf, 2),
            "word_count": len(lines),
            "lines": lines,
        }
