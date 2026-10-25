"""Simulate PAD attacks against the verification endpoint.

Real PAD testing (iBeta) requires physical PAIs and a camera. In CI we
simulate the *decision path*:
  - transform a bona fide image into "printed" (JPEG recompress + downscale)
  - "screen replay" (upscale + gamma shift + moiré-ish noise)
  - "paper mask" (crop face region + flat-fill background)

This catches regressions where the liveness/antispoof service stops
distinguishing these patterns, without claiming ISO certification.
"""
import io
from typing import List

import numpy as np
from PIL import Image, ImageEnhance


def _reload(img_bytes: bytes) -> Image.Image:
    return Image.open(io.BytesIO(img_bytes)).convert("RGB")


def _dump(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def simulate_printed(img_bytes: bytes) -> bytes:
    """Downscale + JPEG recompress (simulates a printed photo)."""
    img = _reload(img_bytes).resize((320, 320), Image.BILINEAR)
    return _dump(img)


def simulate_screen_replay(img_bytes: bytes) -> bytes:
    """Upscale + gamma + additive moiré pattern."""
    img = _reload(img_bytes).resize((800, 800), Image.BICUBIC)
    img = ImageEnhance.Brightness(img).enhance(1.15)
    arr = np.asarray(img, dtype=np.int16)
    h, w, _ = arr.shape
    y, x = np.mgrid[0:h, 0:w]
    moire = (8 * np.sin(2 * np.pi * x / 7) + 8 * np.sin(2 * np.pi * y / 11))[..., None]
    arr = np.clip(arr + moire, 0, 255).astype(np.uint8)
    return _dump(Image.fromarray(arr))


def simulate_paper_mask(img_bytes: bytes) -> bytes:
    """Crop center (face) and flatten the background."""
    img = _reload(img_bytes)
    w, h = img.size
    face = img.crop((int(w * 0.25), int(h * 0.15), int(w * 0.75), int(h * 0.85)))
    canvas = Image.new("RGB", (w, h), (230, 230, 230))
    canvas.paste(face, (int(w * 0.25), int(h * 0.15)))
    return _dump(canvas)


SIMULATORS = {
    "pad_level1_printed": simulate_printed,
    "pad_level1_screen": simulate_screen_replay,
    "pad_level1_paper_mask": simulate_paper_mask,
}


def all_attacks(img_bytes: bytes) -> List[tuple]:
    return [(name, fn(img_bytes)) for name, fn in SIMULATORS.items()]
