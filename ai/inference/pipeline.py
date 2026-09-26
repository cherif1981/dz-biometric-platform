import time
from typing import Dict
from ai.preprocessing.image_ops import load_image, preprocess_for_ocr
from ai.detection.card_detector import CardDetector
from ai.detection.face_detector import FaceDetector
from ai.ocr.engine import OCREngine
from ai.ocr.field_extractor_dz import DZFieldExtractor   # ← النسخة المحسّنة
from ai.validation.validators import ImageValidator, ResultValidator

class BiometricPipeline:
    def __init__(self):
        self.card_detector = CardDetector()
        self.face_detector = FaceDetector()
        self.ocr_engine = OCREngine()
        self.field_extractor = DZFieldExtractor()   # ← محسّن
        self.image_validator = ImageValidator()
        self.result_validator = ResultValidator()

    def process_card(self, source) -> Dict:
        start = time.time()
        image = load_image(source)
        valid, msg = self.image_validator.validate(image)
        if not valid:
            return {"success": False, "error": msg}
        card, bbox = self.card_detector.detect(image)
        processed = preprocess_for_ocr(card)
        ocr_result = self.ocr_engine.extract(processed)
        fields = self.field_extractor.extract(ocr_result["text"])
        validation = self.result_validator.validate_ocr(fields)
        return {
            "success": True,
            "text": ocr_result["text"],
            "confidence": ocr_result["confidence"],
            "fields": fields,
            "validation": validation,
            "card_bbox": bbox,
            "processing_time": round(time.time() - start, 3),
        }

    def detect_faces(self, source) -> Dict:
        start = time.time()
        image = load_image(source)
        result = self.face_detector.detect(image)
        result["processing_time"] = round(time.time() - start, 3)
        return result

    def verify_faces(self, source1, source2) -> Dict:
        start = time.time()
        img1 = load_image(source1)
        img2 = load_image(source2)
        result = self.face_recognizer.verify(img1, img2)
        result["processing_time"] = round(time.time() - start, 3)
        return result


# instance جاهزة للاستيراد من main.py
pipeline = BiometricPipeline()
