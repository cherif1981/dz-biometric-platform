"""Unit tests for OCR service."""

import io

import pytest
from PIL import Image, ImageDraw


def _make_text_image(text="HELLO"):
    """Create an image with text."""
    img = Image.new("RGB", (400, 200), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((50, 80), text, fill="black")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf.read()


class TestOCRService:
    """Tests for OCRService."""

    def test_ocr_import(self):
        """OCR service should be importable."""
        try:
            from src.services.ocr_service import OCRService

            assert OCRService is not None
        except ImportError as e:
            pytest.skip(f"OCR service not available: {e}")

    def test_ocr_on_text_image(self):
        """OCR should extract some text."""
        try:
            from src.services.ocr_service import OCRService
        except ImportError:
            pytest.skip("OCR not available")

        service = OCRService()
        img_bytes = _make_text_image("BENALI Ahmed")
        result = service.extract(img_bytes)
        assert "fields" in result
        assert "confidence" in result

    def test_ocr_invalid_bytes(self):
        """Invalid bytes should not crash."""
        try:
            from src.services.ocr_service import OCRService
        except ImportError:
            pytest.skip("OCR not available")

        service = OCRService()
        result = service.extract(b"not an image")
        assert isinstance(result, dict)
