"""محرك OCR للنصوص العربية والفرنسية"""
import pytesseract


def run_ocr(image, lang='ara+fra', psm=6):
    """تشغيل OCR على الصورة"""
    config = f'--oem 1 --psm {psm}'
    return pytesseract.image_to_string(image, lang=lang, config=config)


def get_ocr_data(image, lang='ara+fra', psm=6, min_confidence=30):
    """استخراج النص مع مستويات الثقة"""
    config = f'--oem 1 --psm {psm}'
    data = pytesseract.image_to_data(
        image, lang=lang, config=config,
        output_type=pytesseract.Output.DICT
    )

    results = []
    n = len(data['text'])
    for i in range(n):
        text = data['text'][i].strip()
        conf = int(data['conf'][i])
        if text and conf > min_confidence:
            results.append({
                'text': text,
                'confidence': conf,
                'x': data['left'][i],
                'y': data['top'][i],
                'w': data['width'][i],
                'h': data['height'][i]
            })
    return results