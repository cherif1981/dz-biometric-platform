from ai.preprocessing.image_utils import correct_skew, crop_card
from ai.models.detection.detector import detect_card
from ai.models.ocr.reader import extract_text

def process_card(image_bytes: bytes) -> dict:
    """يأخذ صورة خام ويعيد بيانات البطاقة المستخرجة"""
    image = decode_image(image_bytes)
    box = detect_card(image)
    cropped = crop_card(image, box)
    corrected = correct_skew(cropped)
    fields = extract_text(corrected)
    return fields