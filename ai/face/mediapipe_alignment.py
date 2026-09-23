"""
MediaPipe Face Alignment for DZ Biometric Platform
Provides fast and accurate face alignment using 468 facial landmarks.
"""

import cv2
import numpy as np
from typing import Optional, Tuple, Dict, List
import logging

logger = logging.getLogger(__name__)

try:
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    logger.warning("mediapipe not installed. Run: pip install mediapipe")


# النقاط المرجعية القياسية لوجه أمامي (112x112)
# مبنية على العينين + الأنف + زاويتي الفم
REFERENCE_5_POINTS = np.array([
    [38.2946, 51.6963],   # Left eye center
    [73.5318, 51.5014],   # Right eye center
    [56.0252, 71.7366],   # Nose tip
    [41.5493, 92.3655],   # Mouth left
    [70.7299, 92.2041],   # Mouth right
], dtype=np.float32)


class MediaPipeAligner:
    """Face alignment using MediaPipe Face Mesh (468 landmarks)."""

    def __init__(
        self,
        static_image_mode: bool = True,
        max_num_faces: int = 1,
        min_detection_confidence: float = 0.5,
        refine_landmarks: bool = True,
    ):
        if not MEDIAPIPE_AVAILABLE:
            raise ImportError(
                "mediapipe is required. Install with: pip install mediapipe"
            )

        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=static_image_mode,
            max_num_faces=max_num_faces,
            refine_landmarks=refine_landmarks,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=0.5,
        )

    def _to_rgb(self, image: np.ndarray) -> np.ndarray:
        if image.ndim == 2:
            return cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        if image.shape[2] == 4:
            return cv2.cvtColor(image, cv2.COLOR_BGRA2RGB)
        return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    def get_landmarks(self, image: np.ndarray) -> Optional[np.ndarray]:
        """
        Extract all 468 landmarks as pixel coordinates (N, 2).
        Returns None if no face is detected.
        """
        rgb = self._to_rgb(image)
        results = self.face_mesh.process(rgb)

        if not results.multi_face_landmarks:
            return None

        h, w = image.shape[:2]
        landmarks = results.multi_face_landmarks[0]

        points = np.array(
            [[lm.x * w, lm.y * h] for lm in landmarks.landmark],
            dtype=np.float32,
        )
        return points

    def get_key_landmarks(self, image: np.ndarray) -> Optional[Dict[str, np.ndarray]]:
        """
        Return the most important landmarks for alignment and quality checks.
        """
        points = self.get_landmarks(image)
        if points is None:
            return None

        # MediaPipe Face Mesh indices
        return {
            "left_eye_center": (points[33] + points[133]) / 2,
            "right_eye_center": (points[263] + points[362]) / 2,
            "left_eye_outer": points[33],
            "left_eye_inner": points[133],
            "right_eye_outer": points[263],
            "right_eye_inner": points[362],
            "nose_tip": points[1],
            "mouth_left": points[61],
            "mouth_right": points[291],
            "chin": points[152],
            "forehead": points[10],
            "all_points": points,
        }

    def get_5_points(self, image: np.ndarray) -> Optional[np.ndarray]:
        """Return 5 classic points used for similarity transform."""
        keys = self.get_key_landmarks(image)
        if keys is None:
            return None

        return np.array(
            [
                keys["left_eye_center"],
                keys["right_eye_center"],
                keys["nose_tip"],
                keys["mouth_left"],
                keys["mouth_right"],
            ],
            dtype=np.float32,
        )

    def align(
        self,
        image: np.ndarray,
        output_size: Tuple[int, int] = (112, 112),
    ) -> Optional[np.ndarray]:
        """
        Align face using 5-point similarity transform.
        Returns aligned RGB image of shape (H, W, 3) or None.
        """
        src_points = self.get_5_points(image)
        if src_points is None:
            return None

        # Estimate similarity transform (rotation + scale + translation)
        transform, inliers = cv2.estimateAffinePartial2D(
            src_points,
            REFERENCE_5_POINTS,
            method=cv2.LMEDS,
        )

        if transform is None:
            return None

        rgb = self._to_rgb(image)
        aligned = cv2.warpAffine(
            rgb,
            transform,
            output_size,
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REPLICATE,
        )
        return aligned

    def align_bgr(
        self,
        image: np.ndarray,
        output_size: Tuple[int, int] = (112, 112),
    ) -> Optional[np.ndarray]:
        """Same as align() but returns BGR (for OpenCV pipelines)."""
        aligned_rgb = self.align(image, output_size)
        if aligned_rgb is None:
            return None
        return cv2.cvtColor(aligned_rgb, cv2.COLOR_RGB2BGR)

    def face_quality_score(self, image: np.ndarray) -> float:
        """
        Simple quality score based on eye distance and detection confidence.
        Returns value between 0.0 and 1.0.
        """
        keys = self.get_key_landmarks(image)
        if keys is None:
            return 0.0

        eye_dist = np.linalg.norm(
            keys["right_eye_center"] - keys["left_eye_center"]
        )
        # Normalize: good faces usually have eye distance > 40 px
        size_score = min(1.0, eye_dist / 60.0)
        return round(float(size_score), 3)

    def close(self):
        self.face_mesh.close()


# ------------------------------------------------------------------
# Convenience functions
# ------------------------------------------------------------------

_aligner_instance: Optional[MediaPipeAligner] = None


def get_aligner() -> MediaPipeAligner:
    global _aligner_instance
    if _aligner_instance is None:
        _aligner_instance = MediaPipeAligner()
    return _aligner_instance


def align_face(
    image: np.ndarray,
    output_size: Tuple[int, int] = (112, 112),
) -> Optional[np.ndarray]:
    """Quick helper: align a face and return RGB image."""
    return get_aligner().align(image, output_size)


def get_face_landmarks(image: np.ndarray) -> Optional[np.ndarray]:
    """Quick helper: return all 468 landmarks."""
    return get_aligner().get_landmarks(image)