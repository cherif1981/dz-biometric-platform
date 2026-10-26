"""
Anti-Spoofing Module using ONNX model (MiniFASNetV2).
Replaces the placeholder that returned fixed values.

Security principle: absence of face or model failure MUST NOT be treated as success.
"""

from typing import Dict, Optional

import cv2
import numpy as np
import onnxruntime as ort


class AntiSpoofing:
    def __init__(
        self,
        model_path: str = "MiniFASNetV2.onnx",
        scale: float = 2.7,
        threshold: float = 0.5,
        input_size: tuple = (80, 80),
    ):
        self.session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
        self.input_name = self.session.get_inputs()[0].name
        self.input_size = input_size
        self.scale = scale
        self.threshold = threshold
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

    def _detect_face(self, image: np.ndarray) -> Optional[list]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4)
        if len(faces) == 0:
            return None
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
        return [x, y, x + w, y + h]

    def _crop_face(self, image: np.ndarray, bbox: list) -> np.ndarray:
        x1, y1, x2, y2 = bbox
        src_h, src_w = image.shape[:2]
        box_w, box_h = x2 - x1, y2 - y1
        scale = min((src_h - 1) / box_h, (src_w - 1) / box_w, self.scale)
        new_w, new_h = box_w * scale, box_h * scale
        center_x, center_y = x1 + box_w / 2, y1 + box_h / 2
        x1 = max(0, int(center_x - new_w / 2))
        y1 = max(0, int(center_y - new_h / 2))
        x2 = min(src_w - 1, int(center_x + new_w / 2))
        y2 = min(src_h - 1, int(center_y + new_h / 2))
        cropped = image[y1 : y2 + 1, x1 : x2 + 1]
        return cv2.resize(cropped, self.input_size)

    def _preprocess(self, face: np.ndarray) -> np.ndarray:
        face = face.astype(np.float32)
        face = np.transpose(face, (2, 0, 1))
        face = np.expand_dims(face, axis=0)
        return face

    def check(self, image_bytes: bytes) -> Dict:
        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        except Exception as e:
            return {"spoof": True, "score": 0.0, "error": f"Decode error: {e}"}

        if image is None:
            return {"spoof": True, "score": 0.0, "error": "Invalid image format"}

        bbox = self._detect_face(image)
        if bbox is None:
            return {"spoof": True, "score": 0.0, "error": "No face detected"}

        try:
            face = self._crop_face(image, bbox)
            input_tensor = self._preprocess(face)
        except Exception as e:
            return {"spoof": True, "score": 0.0, "error": f"Preprocess error: {e}"}

        try:
            outputs = self.session.run(None, {self.input_name: input_tensor})
            logits = outputs[0]
        except Exception as e:
            return {"spoof": True, "score": 0.0, "error": f"Inference error: {e}"}

        e_x = np.exp(logits - np.max(logits, axis=1, keepdims=True))
        probs = e_x / e_x.sum(axis=1, keepdims=True)
        real_prob = float(probs[0, 1])
        is_spoof = real_prob < self.threshold
        return {"spoof": is_spoof, "score": real_prob, "error": None}
