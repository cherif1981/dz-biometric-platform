import pytesseract
import numpy as np
from typing import Dict
from ai.configs.settings import settings

class OCREngine:
    def extract(self, image: np.ndarray) -> Dict:
        config = f"--oem {settings.OCR_OEM} --psm {settings.OCR_PSM}"
        data = pytesseract.image_to_data(
            image, lang=settings.OCR_LANGUAGES,
            config=config, output_type=pytesseract.Output.DICT
        )
        words, confs = [], []
        for i, txt in enumerate(data["text"]):
            if txt.strip():
                words.append(txt)
                try:
                    confs.append(float(data["conf"][i]))
                except (ValueError, TypeError):
                    pass
        text = " ".join(words)
        avg_conf = sum(confs) / len(confs) if confs else 0.0
        return {
            "text": text,
            "confidence": round(avg_conf, 2),
            "word_count": len(words),
        }
