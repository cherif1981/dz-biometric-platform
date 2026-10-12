"""SEC-07: upload size + content validation."""
import io
import pytest
from PIL import Image


def _make_jpeg(w=400, h=400, color=(200, 200, 200)) -> bytes:
    img = Image.new("RGB", (w, h), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_valid_jpeg_passes():
    from src.core.upload_limits import validate_image_bytes
    mime = validate_image_bytes(_make_jpeg())
    assert mime == "image/jpeg"


def test_empty_bytes_rejected():
    from src.core.upload_limits import validate_image_bytes
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as ei:
        validate_image_bytes(b"")
    assert ei.value.status_code == 400


def test_non_image_rejected():
    from src.core.upload_limits import validate_image_bytes
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as ei:
        validate_image_bytes(b"this is not an image at all, no magic bytes")
    assert ei.value.status_code == 415


def test_oversized_rejected():
    from src.core.upload_limits import validate_image_bytes, MAX_UPLOAD_BYTES
    from fastapi import HTTPException
    big = _make_jpeg() + b"\x00" * (MAX_UPLOAD_BYTES + 10)
    with pytest.raises(HTTPException) as ei:
        validate_image_bytes(big)
    assert ei.value.status_code == 413


def test_dimensions_too_large_rejected():
    from src.core.upload_limits import validate_image_bytes
    from fastapi import HTTPException
    # 9000x9000 exceeds MAX_IMAGE_DIMENSION (8000)
    img = Image.new("RGB", (9000, 9000), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=10)
    with pytest.raises(HTTPException) as ei:
        validate_image_bytes(buf.getvalue())
    assert ei.value.status_code == 400


def test_sniff_mime():
    from src.core.upload_limits import sniff_image_mime
    assert sniff_image_mime(_make_jpeg()) == "image/jpeg"
    assert sniff_image_mime(b"\x89PNG\r\n\x1a\n" + b"\x00" * 20) == "image/png"
    assert sniff_image_mime(b"garbage") is None
