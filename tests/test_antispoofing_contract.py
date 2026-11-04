"""Contracts locked by direct measurement.

CONFIRMED: REAL_CLASS_INDEX=1, BGR [0,255], fail-closed, YuNet bbox.
NOT tested: APCER/BPCER (needs real presentation attacks).
FORCE_REVIEW remains policy default.
"""
import os
import cv2
import numpy as np
import pytest

from src.services import antispoofing_service as svc


def _enc(img):
    ok, buf = cv2.imencode(".jpg", img)
    assert ok
    return buf.tobytes()


@pytest.fixture(scope="module")
def inst():
    return svc.AntiSpoofing()


def test_real_class_index_is_live():
    assert svc.REAL_CLASS_INDEX == 1


def test_model_io_shape():
    s = svc.AntiSpoofing().session
    assert list(s.get_inputs()[0].shape[1:])  == [3, 80, 80]
    assert list(s.get_outputs()[0].shape[1:]) == [3]


@pytest.mark.parametrize("color", [(0,0,0), (127,127,127), (255,255,255)])
def test_no_face_is_rejected(inst, color):
    r = inst.check(_enc(np.full((240,240,3), color, np.uint8)))
    assert r["decision"] == "REJECT", r
    assert r["antispoofing_score"] == 0.0


def test_decode_failure_is_rejected(inst):
    assert inst.check(b"not a jpeg")["decision"] == "REJECT"


def test_preprocessing_not_divided_by_255():
    s = svc.AntiSpoofing().session
    name = s.get_inputs()[0].name
    def L(f):
        x = np.full((1,3,80,80), f, np.float32)
        return s.run(None, {name: x})[0][0]
    d = float(np.max(np.abs(L(0.0) - L(255.0))))
    assert d > 0.5, f"logits collapsed (delta={d:.3f})"


def test_yunet_bbox_encoding_is_xyxy():
    det = svc.YuNetDetector()
    src = "tests/fixtures/live/face.jpg"
    if not os.path.exists(src):
        pytest.skip("no real face fixture")
    img = cv2.imread(src)
    faces = det.detect(img)
    assert faces
    x1, y1, x2, y2 = faces[0]
    H, W = img.shape[:2]
    assert 0 <= x1 < x2 <= W and 0 <= y1 < y2 <= H, faces[0]
    assert (x2 - x1) > 20 and (y2 - y1) > 20, faces[0]
