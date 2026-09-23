import cv2
import numpy as np
import face_recognition
from typing import Optional, Tuple


# النقاط المرجعية القياسية (وجه أمامي 112x112)
REFERENCE_LANDMARKS = np.array([
    [38.2946, 51.6963],   # العين اليسرى
    [73.5318, 51.5014],   # العين اليمنى
    [56.0252, 71.7366],   # الأنف
    [41.5493, 92.3655],   # زاوية الفم اليسرى
    [70.7299, 92.2041],   # زاوية الفم اليمنى
], dtype=np.float32)


def get_5_landmarks(image_rgb: np.ndarray, face_location: Tuple[int, int, int, int]) -> Optional[np.ndarray]:
    """
    استخراج 5 نقاط رئيسية من الوجه.
    face_location: (top, right, bottom, left)
    """
    landmarks = face_recognition.face_landmarks(image_rgb, [face_location])
    if not landmarks:
        return None

    lm = landmarks[0]

    try:
        left_eye = np.mean(lm["left_eye"], axis=0)
        right_eye = np.mean(lm["right_eye"], axis=0)
        nose = np.mean(lm["nose_tip"], axis=0)
        mouth_left = lm["top_lip"][0]
        mouth_right = lm["top_lip"][6]

        points = np.array([
            left_eye,
            right_eye,
            nose,
            mouth_left,
            mouth_right,
        ], dtype=np.float32)
        return points
    except Exception:
        return None


def align_face(
    image: np.ndarray,
    output_size: Tuple[int, int] = (112, 112),
    face_location: Optional[Tuple[int, int, int, int]] = None,
) -> Optional[np.ndarray]:
    """
    محاذاة الوجه باستخدام Similarity Transform.
    
    Returns:
        صورة الوجه المحاذاة بحجم output_size، أو None إذا فشل.
    """
    # تحويل إلى RGB إذا لزم
    if image.ndim == 2:
        rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
    elif image.shape[2] == 4:
        rgb = cv2.cvtColor(image, cv2.COLOR_BGRA2RGB)
    else:
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    # اكتشاف الوجه إذا لم يُمرر
    if face_location is None:
        locations = face_recognition.face_locations(rgb, model="hog")
        if not locations:
            return None
        # أكبر وجه
        face_location = max(locations, key=lambda loc: (loc[2]-loc[0])*(loc[1]-loc[3]))

    src_points = get_5_landmarks(rgb, face_location)
    if src_points is None:
        return None

    # حساب التحويل (Similarity Transform)
    # نستخدم estimateAffinePartial2D لأنه يدعم الدوران + التكبير + الإزاحة فقط
    transform_matrix, _ = cv2.estimateAffinePartial2D(
        src_points,
        REFERENCE_LANDMARKS,
        method=cv2.LMEDS,
    )

    if transform_matrix is None:
        return None

    # تطبيق التحويل
    aligned = cv2.warpAffine(
        rgb,
        transform_matrix,
        output_size,
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REPLICATE,
    )

    return aligned


def align_and_encode(image: np.ndarray, recognizer) -> Optional[np.ndarray]:
    """
    محاذاة الوجه ثم استخراج الـ embedding.
    """
    aligned = align_face(image)
    if aligned is None:
        return None

    # تحويل مرة أخرى إلى BGR لأن بعض النماذج تتوقع ذلك
    aligned_bgr = cv2.cvtColor(aligned, cv2.COLOR_RGB2BGR)
    return recognizer.encode(aligned_bgr)