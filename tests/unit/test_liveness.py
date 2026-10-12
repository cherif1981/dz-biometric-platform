"""Unit tests for liveness detection."""
import io
import pytest
from PIL import Image

from src.services.liveness_service import LivenessService


def _make_image(color=(200, 200, 200), size=(256, 256)):
    """Helper: create a JPEG image in bytes."""
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf.read()


class TestLivenessService:
    """Tests for LivenessService."""

    def setup_method(self):
        self.service = LivenessService(threshold=0.5)

    def test_uniform_image_low_score(self):
        """Uniform image should produce low liveness score."""
        img_bytes = _make_image(color=(200, 200, 200))
        result = self.service.check(img_bytes)
        assert "score" in result
        assert 0.0 <= result["score"] <= 1.0
        assert result["score"] < 0.5

    def test_noisy_image_higher_score(self):
        """Noisy image should produce higher score."""
        import numpy as np
        arr = np.random.randint(0, 255, (256, 256, 3), dtype=np.uint8)
        img = Image.fromarray(arr)
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)
        result = self.service.check(buf.read())
        assert result["score"] > 0.3

    def test_invalid_bytes(self):
        """Invalid bytes should return 0 score."""
        result = self.service.check(b"not an image")
        assert result["score"] == 0.0
        assert result["is_live"] is False

    def test_components_returned(self):
        """Result should include component scores."""
        img_bytes = _make_image()
        result = self.service.check(img_bytes)
        assert "components" in result
        assert "lap" in result["components"]
        assert "hf" in result["components"]
        assert "color" in result["components"]
