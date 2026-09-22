"""محرك القرار النهائي (يدمج OCR + Face)"""
from datetime import datetime


def combine_ocr_and_face(ocr_result, face_result):
    """دمج نتيجة OCR و Face في قرار نهائي متعدد الإشارات"""
    ocr_ok = bool(ocr_result.get('validation', {}).get('is_valid', False))
    ocr_conf = float(ocr_result.get('overall_confidence', 0))

    face_matched = bool(face_result.get('face_verification', {}).get('matched', False))
    face_sim = float(face_result.get('face_verification', {}).get('similarity_percent', 0))

    if face_matched and face_sim >= 50 and ocr_ok:
        decision, reason, risk = "verified", "جميع الإشارات إيجابية", "low"
    elif face_matched and face_sim >= 60:
        decision, reason, risk = "manual_review", "بيانات المستند تحتاج مراجعة", "medium"
    elif ocr_ok and face_sim >= 40:
        decision, reason, risk = "manual_review", "تطابق الوجه ضعيف", "medium"
    else:
        decision, reason, risk = "rejected", "فشل التحقق", "high"

    overall_conf = float(ocr_conf * 0.4 + face_sim * 0.6)

    return {
        "status": "success",
        "decision": decision,
        "reason": reason,
        "risk_level": risk,
        "combined_confidence": round(overall_conf, 2),
        "ocr": ocr_result,
        "face": face_result,
        "timestamp": datetime.utcnow().isoformat()
    }