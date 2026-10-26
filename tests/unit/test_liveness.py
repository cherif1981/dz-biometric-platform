"""
Tests for the ONNX-based liveness service.

Previous tests expected `components` (sharpness, saturation, FFT energy)
from the old heuristic. Those components no longer exist — the detector
now delegates to a trained ONNX model. These tests verify the new
fail-closed contract instead.
"""

import cv2
import numpy as np
import pytest

from src.services.liveness_service import LivenessService


def _encode_jpeg(img: np.ndarray) -> bytes:
    ok, buf = cv2.imencode(".jpg", img)
    assert ok, "failed to encode image"
    return buf.tobytes()


class TestLivenessService:
    def setup_method(self):
        self.service = LivenessService(threshold=0.5)

    def test_threshold_is_injected(self):
        assert self.service.threshold == 0.5

    def test_blank_image_fails_closed(self):
        """Blank image has no face -> must NOT be considered live."""
        blank = np.zeros((200, 200, 3), dtype=np.uint8)
        result = self.service.check(_encode_jpeg(blank))
        assert result["is_live"] is False
        assert result["score"] == 0.0
        assert result.get("error") is not None

    def test_invalid_bytes_fails_closed(self):
        result = self.service.check(b"not-an-image-at-all")
        assert result["is_live"] is False
        assert result["score"] == 0.0
        assert result.get("error") is not None

    def test_noisy_image_does_not_crash(self):
        """Random noise has no face -> still fail-closed, no exception."""
        rng = np.random.default_rng(42)
        noise = rng.integers(0, 256, (200, 200, 3), dtype=np.uint8)
        result = self.service.check(_encode_jpeg(noise))
        assert result["is_live"] is False
        assert result["score"] == 0.0

    def test_result_has_required_keys(self):
        blank = np.zeros((200, 200, 3), dtype=np.uint8)
        result = self.service.check(_encode_jpeg(blank))
        for key in ("is_live", "score", "threshold", "error"):
            assert key in result
