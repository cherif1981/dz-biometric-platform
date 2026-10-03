import time
from typing import Dict
import numpy as np

from ai.preprocessing.image_ops import load_image, preprocess_for_ocr
from ai.detection.card_detector import CardDetector
from ai.detection.face_detector import FaceDetector
from ai.ocr.engine import OCREngine
from ai.ocr.field_extractor_dz import DZFieldExtractor
from ai.validation.validators import ImageValidator, ResultValidator


class BiometricPipeline:
    def __init__(self):
        self.card_detector = CardDetector()
        self.face_detector = FaceDetector()
        self.ocr_engine = OCREngine()
        self.field_extractor = DZFieldExtractor()
        self.image_validator = ImageValidator()
        self.result_validator = ResultValidator()

        self.face_app = self.face_detector.app

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

    faces1 = self.face_app.get(img1)
    faces2 = self.face_app.get(img2)

    if not faces1 or not faces2:
        return {
            "success": False,
            "verified": False,
            "similarity": 0.0,
            "distance": 1.0,
            "message": "لم يتم اكتشاف وجه في إحدى الصورتين",
            "processing_time": round(time.time() - start, 3),
        }

    e1 = faces1[0].embedding
    e2 = faces2[0].embedding
    sim = float(np.dot(e1, e2) / (np.linalg.norm(e1) * np.linalg.norm(e2) + 1e-8))
    distance = 1.0 - sim
    verified = sim >= 0.5

    return {
        "success": True,
        "verified": verified,
        "similarity": round(sim, 4),
        "distance": round(distance, 4),
        "message": "✅ تطابق" if verified else "❌ لا يوجد تطابق",
        "processing_time": round(time.time() - start, 3),
    }


pipeline = BiometricPipeline()
