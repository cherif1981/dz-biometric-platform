import cv2
import numpy as np
from PIL import Image
from io import BytesIO
from typing import Union

def load_image(source: Union[bytes, str, np.ndarray]) -> np.ndarray:
    if isinstance(source, np.ndarray):
        return source
    if isinstance(source, bytes):
        img = Image.open(BytesIO(source)).convert("RGB")
        return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    return cv2.imread(str(source))

def to_grayscale(image):
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

def denoise(image, strength=30):
    return cv2.fastNlMeansDenoising(image, h=strength)

def enhance_contrast(image):
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(image)

def binarize(image):
    return cv2.adaptiveThreshold(
        image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )

def deskew(image):
    coords = np.column_stack(np.where(image > 0))
    if len(coords) < 10:
        return image
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = 90 + angle
    (h, w) = image.shape[:2]
    M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    return cv2.warpAffine(image, M, (w, h),
                          flags=cv2.INTER_CUBIC,
                          borderMode=cv2.BORDER_REPLICATE)

def preprocess_for_ocr(image):
    gray = to_grayscale(image)
    gray = denoise(gray)
    gray = enhance_contrast(gray)
    gray = deskew(gray)
    return binarize(gray)
