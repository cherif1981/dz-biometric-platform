"""Biometric AI — Quality/Liveness/AntiSpoof موحد ومفصول عن Similarity."""

from dataclasses import dataclass, field
from typing import Dict, Optional, Any
import io

import cv2
import numpy as np
from loguru import logger


@dataclass
class FaceQualityResult:
    """نتيجة تقييم جودة الوجه."""
    overall: float = 0.0
    sharpness: float = 0.0
    brightness: float = 0.0
    contrast: float = 0.0
    face_size: float = 0.0
    pose_score: float = 0.0
    is_acceptable: bool = False
    reasons: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "overall": self.overall,
            "sharpness": self.sharpness,
            "brightness": self.brightness,
            "contrast": self.contrast,
            "face_size": self.face_size,
            "pose_score": self.pose_score,
            "is_acceptable": self.is_acceptable,
            "reasons": self.reasons,
        }


@dataclass
class LivenessResult:
    """نتيجة فحص الحياة."""
    score: float = 0.0
    is_real: bool = False
    method: str = "heuristic_v1"
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AntiSpoofResult:
    """نتيجة مكافحة الانتحال."""
    score: float = 0.0
    is_live: bool = False
    method: str = "heuristic_v1"
    details: Dict[str, Any] = field(default_factory=dict)


class BiometricAI:
    """
    طبقة موحدة تدمج:
    - Face Quality Assessment (منفصل عن Similarity)
    - Liveness Detection
    - Anti-Spoofing Detection

    تستقبل خدمة الوجه الحالية (InsightFace) اختياريًا.
    إن لم تُمرَّر، تعمل في وضع heuristic.
    """

    def __init__(self, face_app=None, min_quality: float = 0.40):
        self.face_app = face_app
        self.min_quality = min_quality
        logger.info(f"BiometricAI initialized | face_app={'yes' if face_app else 'no'} | "
                    f"min_quality={min_quality}")

    # ==================== Face Quality ====================
    def assess_face_quality(self, image_bytes: bytes) -> FaceQualityResult:
        """
        تقييم جودة الوجه بشكل مستقل عن التشابه.
        """
        img = self._decode(image_bytes)
        if img is None:
            return FaceQualityResult(reasons=["INVALID_IMAGE"])

        reasons = []
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 1. الحدة
        sharpness_raw = cv2.Laplacian(gray, cv2.CV_64F).var()
        sharpness = min(1.0, sharpness_raw / 500.0)
        if sharpness < 0.3:
            reasons.append("BLURRY")

        # 2. الإضاءة
        brightness_raw = float(np.mean(gray)) / 255.0
        brightness = max(0.0, 1.0 - abs(brightness_raw - 0.5) * 2.0)
        if brightness_raw < 0.20:
            reasons.append("TOO_DARK")
        elif brightness_raw > 0.85:
            reasons.append("TOO_BRIGHT")

        # 3. التباين
        contrast = min(1.0, float(gray.std()) / 80.0)
        if contrast < 0.3:
            reasons.append("LOW_CONTRAST")

        # 4. حجم/زاوية الوجه
        face_size = 0.5
        pose_score = 0.5
        if self.face_app is not None:
            try:
                faces = self._call_face_app(img)
                if faces:
                    f = faces[0]
                    x1, y1, x2, y2 = f.bbox
                    w, h = max(0, x2 - x1), max(0, y2 - y1)
                    area_ratio = (w * h) / (img.shape[0] * img.shape[1])
                    face_size = min(1.0, area_ratio * 8.0)

                    # زاوية (من landmarks إن وُجدت)
                    if hasattr(f, "pose") and f.pose is not None:
                        yaw, pitch, roll = f.pose
                        max_angle = max(abs(yaw), abs(pitch), abs(roll))
                        pose_score = max(0.0, 1.0 - max_angle / 45.0)
                    elif hasattr(f, "kps") and f.kps is not None:
                        # تقدير بسيط من kps: نسبة المسافة بين العينين
                        kps = f.kps
                        if len(kps) >= 5:
                            eye_dist = np.linalg.norm(kps[0] - kps[1])
                            face_w = max(w, 1)
                            ratio = eye_dist / face_w
                            pose_score = min(1.0, ratio * 1.5)
                else:
                    face_size = 0.0
                    pose_score = 0.0
                    reasons.append("NO_FACE_DETECTED")
            except Exception as e:
                logger.warning(f"Face quality via face_app failed: {e}")

        # المزيج
        overall = (sharpness * 0.30
                   + brightness * 0.20
                   + contrast * 0.15
                   + face_size * 0.20
                   + pose_score * 0.15)

        overall = round(float(overall), 4)
        is_acceptable = overall >= self.min_quality

        if not is_acceptable:
            reasons.append(f"LOW_QUALITY:{overall:.3f}")

        return FaceQualityResult(
            overall=overall,
            sharpness=round(float(sharpness), 4),
            brightness=round(float(brightness), 4),
            contrast=round(float(contrast), 4),
            face_size=round(float(face_size), 4),
            pose_score=round(float(pose_score), 4),
            is_acceptable=is_acceptable,
            reasons=reasons,
        )

    # ==================== Liveness ====================
    def check_liveness(
        self,
        image_bytes: bytes,
        external_result: Optional[Dict[str, Any]] = None,
    ) -> LivenessResult:
        """
        إن مُرّرت external_result من خدمة Liveness الحالية، يستخدمها.
        وإلا يعمل heuristic.
        """
        if external_result is not None:
            score = float(external_result.get("score", 0.0))
            return LivenessResult(
                score=score,
                is_real=score >= 0.50,
                method=external_result.get("method", "external"),
                details=external_result,
            )

        img = self._decode(image_bytes)
        if img is None:
            return LivenessResult(score=0.0, is_real=False,
                                  details={"error": "invalid_image"})

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Heuristic: بناءً على الملمس (الوجه الحقيقي فيه تفاصيل أكثر من الصورة)
        lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        texture_score = min(1.0, lap_var / 400.0)

        # توزيع الألوان (الصور المُعاد تصويرها تفقد تشبعات)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        saturation = float(np.mean(hsv[:, :, 1])) / 255.0
        sat_score = min(1.0, saturation * 1.5)

        # تفاصيل عالية التردد (FFT)
        f = np.fft.fft2(gray)
        fshift = np.fft.fftshift(f)
        magnitude = np.log(np.abs(fshift) + 1)
        h, w = magnitude.shape
        center = magnitude[h//4:3*h//4, w//4:3*w//4]
        outer = magnitude.mean() - center.mean()
        freq_score = min(1.0, max(0.0, outer) / 3.0)

        score = texture_score * 0.40 + sat_score * 0.30 + freq_score * 0.30
        score = round(float(min(1.0, score)), 4)

        return LivenessResult(
            score=score,
            is_real=score >= 0.50,
            method="heuristic_v1",
            details={
                "texture": round(texture_score, 4),
                "saturation": round(sat_score, 4),
                "frequency": round(freq_score, 4),
            },
        )

    # ==================== Anti-Spoofing ====================
    def check_antispoof(
        self,
        image_bytes: bytes,
        external_result: Optional[Dict[str, Any]] = None,
    ) -> AntiSpoofResult:
        if external_result is not None:
            score = float(external_result.get("score", 0.0))
            return AntiSpoofResult(
                score=score,
                is_live=score >= 0.50,
                method=external_result.get("method", "external"),
                details=external_result,
            )

        img = self._decode(image_bytes)
        if img is None:
            return AntiSpoofResult(score=0.0, is_live=False,
                                   details={"error": "invalid_image"})

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 1. Moiré pattern (شاشات)
        f = np.fft.fft2(gray)
        fshift = np.abs(np.fft.fftshift(f))
        h, w = fshift.shape
        # Moiré يظهر كقمم في الترددات العالية خارج المركز
        outer = fshift.copy()
        outer[h//3:2*h//3, w//3:2*w//3] = 0
        moire_ratio = float(outer.sum()) / (fshift.sum() + 1e-6)
        moire_score = 1.0 - min(1.0, moire_ratio * 3.0)

        # 2. تناسق الإضاءة (الصور المُعاد تصويرها فيها انعكاسات)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        v = hsv[:, :, 2].astype(np.float32)
        # قياس عدم انتظام الإضاءة
        v_blur = cv2.GaussianBlur(v, (0, 0), 15)
        v_diff = np.abs(v - v_blur)
        illumination_anomaly = float(v_diff.mean()) / 255.0
        illum_score = max(0.0, 1.0 - illumination_anomaly * 5.0)

        # 3. Color diversity (الشاشات تفقد تنوع الألوان)
        color_std = float(img.reshape(-1, 3).std(axis=0).mean()) / 128.0
        color_score = min(1.0, color_std)

        score = moire_score * 0.40 + illum_score * 0.30 + color_score * 0.30
        score = round(float(min(1.0, max(0.0, score))), 4)

        return AntiSpoofResult(
            score=score,
            is_live=score >= 0.50,
            method="heuristic_v1",
            details={
                "moire": round(moire_score, 4),
                "illumination": round(illum_score, 4),
                "color": round(color_score, 4),
            },
        )

    # ==================== Helper ====================
    @staticmethod
    def _decode(image_bytes: bytes):
        try:
            if isinstance(image_bytes, str):
                with open(image_bytes, "rb") as f:
                    image_bytes = f.read()
            arr = np.frombuffer(image_bytes, np.uint8)
            return cv2.imdecode(arr, cv2.IMREAD_COLOR)
        except Exception as e:
            logger.error(f"BiometricAI decode failed: {e}")
            return None
