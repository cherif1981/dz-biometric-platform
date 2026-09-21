"""
EasyOCR Engine مخصص للبطاقات الجزائرية
يستخدم قارئين:
  - قارئ للعربية (ar) مع الإنجليزية
  - قارئ للفرنسية (fr) مع الإنجليزية
ثم يدمج النتائج
"""
import easyocr
import numpy as np
from typing import Dict, List

class EasyOCREngine:
    def __init__(self, gpu: bool = True):
        print("🔄 تحميل نماذج EasyOCR (قد يستغرق دقيقة أول مرة)...")

        # قارئ للعربية (يدعم أيضاً en مع ar)
        self.reader_ar = easyocr.Reader(
            ['ar', 'en'],
            gpu=gpu,
            verbose=False
        )

        # قارئ للفرنسية
        self.reader_fr = easyocr.Reader(
            ['fr', 'en'],
            gpu=gpu,
            verbose=False
        )
        print("✅ تم تحميل النماذج")

    def extract(self, image: np.ndarray) -> Dict:
        """تشغيل القارئين ودمج النتائج"""
        # تشغيل القارئين
        results_ar = self.reader_ar.readtext(image, detail=1, paragraph=False)
        results_fr = self.reader_fr.readtext(image, detail=1, paragraph=False)

        # دمج النتائج (تفادي التكرار بناءً على الموضع)
        merged = self._merge_results(results_ar, results_fr)

        # تجميع النص والثقة
        words, confs = [], []
        for item in merged:
            words.append(item["text"])
            confs.append(item["confidence"])

        text = " ".join(words)
        avg_conf = sum(confs) / len(confs) if confs else 0.0

        return {
            "text": text,
            "confidence": round(avg_conf, 2),
            "word_count": len(words),
            "boxes": [item["bbox"] for item in merged],
            "details": merged,  # تفاصيل كل كلمة
        }

    def _merge_results(self, results_ar: List, results_fr: List) -> List[Dict]:
        """دمج نتائج القارئين مع تفادي التكرار"""
        merged = []
        used_centers = []

        def center_of(bbox):
            xs = [p[0] for p in bbox]
            ys = [p[1] for p in bbox]
            return (sum(xs) / len(xs), sum(ys) / len(ys))

        def is_duplicate(bbox, threshold=15):
            cx, cy = center_of(bbox)
            for (ux, uy) in used_centers:
                if abs(cx - ux) < threshold and abs(cy - uy) < threshold:
                    return True
            return False

        # نأخذ أولاً النتائج العربية (أولوية)
        for (bbox, text, conf) in results_ar:
            if not is_duplicate(bbox):
                merged.append({
                    "text": text,
                    "confidence": conf * 100,
                    "bbox": bbox,
                    "source": "ar",
                })
                used_centers.append(center_of(bbox))

        # ثم الفرنسية (فقط ما لم يُكتشف)
        for (bbox, text, conf) in results_fr:
            if not is_duplicate(bbox):
                merged.append({
                    "text": text,
                    "confidence": conf * 100,
                    "bbox": bbox,
                    "source": "fr",
                })
                used_centers.append(center_of(bbox))

        # ترتيب حسب الموضع (من أعلى إلى أسفل، من يسار إلى يمين)
        merged.sort(key=lambda x: (center_of(x["bbox"])[1] // 20,
                                    center_of(x["bbox"])[0]))

        return merged
