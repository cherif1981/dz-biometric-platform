from functools import lru_cache
import easyocr


@lru_cache(maxsize=1)
def _reader():
    return easyocr.Reader(["ar"], gpu=False)


class ArabicEngine:
    def read(self, image_bytes_or_array) -> dict:
        import numpy as np
        from src.modules.document_reader.preprocessing import to_cv2

        if isinstance(image_bytes_or_array, (bytes, bytearray)):
            img = to_cv2(bytes(image_bytes_or_array))
        else:
            img = image_bytes_or_array

        results = _reader().readtext(img, detail=1, paragraph=False)
        text = "\n".join(r[1] for r in results)
        conf = float(sum(r[2] for r in results) / max(len(results), 1))
        return {"text": text, "confidence": conf, "raw": results}