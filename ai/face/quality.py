"""تقييم جودة الوجه"""


def face_quality_score(face):
    """حساب جودة الوجه (0-1)"""
    bbox = face.bbox
    area = float((bbox[2] - bbox[0]) * (bbox[3] - bbox[1]))
    size_score = min(1.0, area / 50000)
    det_score = float(face.det_score) if hasattr(face, 'det_score') else 1.0
    return float(size_score * 0.4 + det_score * 0.6)