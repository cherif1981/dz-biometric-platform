from typing import List

import numpy as np
import pytesseract
import yaml


class OCREngine:
    """Wrapper around Tesseract."""

    def __init__(self, config_path: str = "configs/model_config.yaml"):
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        self.cfg = cfg["ocr"]
        self.lang = "+".join(self.cfg["languages"])

    def extract_text(self, img: np.ndarray) -> str:
        config = f"--oem {self.cfg['oem']} --psm {self.cfg['psm']}"
        return pytesseract.image_to_string(img, lang=self.lang, config=config)

    def extract_data(self, img: np.ndarray) -> dict:
        data = pytesseract.image_to_data(
            img, lang=self.lang, output_type=pytesseract.Output.DICT
        )
        results: List[dict] = []
        for i, text in enumerate(data["text"]):
            if text.strip():
                results.append(
                    {
                        "text": text,
                        "conf": int(data["conf"][i]),
                        "left": data["left"][i],
                        "top": data["top"][i],
                        "width": data["width"][i],
                        "height": data["height"][i],
                    }
                )
        return {"words": results}