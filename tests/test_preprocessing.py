import os

"""Regression guard against reintroducing the [0,1] bug."""
import numpy as np
import onnxruntime as ort
import pytest

from anti_spoof.decision import Decision, ModelStatus, decide
from anti_spoof.preprocess import LIVE_INDEX, liveness_from_output, preprocess

# ── Model availability guard ──
# Some CI workflows (ci.yml, tests.yml) do not download the ONNX model.
# Skip ONNX-dependent tests rather than fail collection with a confusing
# NoSuchFile from onnxruntime.
_MODEL_PATH_CANDIDATES = [
    os.environ.get("MODEL_PATH"),
    "/content/models/MiniFASNetV2.onnx",
    "MiniFASNetV2.onnx",
]
_MODEL_AVAILABLE = any(p and os.path.exists(p) for p in _MODEL_PATH_CANDIDATES)

skipif_no_model = pytest.mark.skipif(
    not _MODEL_AVAILABLE,
    reason="ONNX model MiniFASNetV2.onnx unavailable "
           "(set MODEL_PATH or download it; security.yml does download it)",
)


MODEL = "MiniFASNetV2.onnx"


@pytest.fixture(scope="module")
def session():
    return ort.InferenceSession(MODEL, providers=["CPUExecutionProvider"])


def _score(s, im):
    out = s.run(None, {"input": preprocess(im)})[0][0]
    return liveness_from_output(out)


@skipif_no_model
def test_black_rejected(session):
    assert _score(session, np.zeros((200, 200, 3), np.uint8)) < 0.1


@skipif_no_model
def test_white_not_accepted(session):
    assert _score(session, np.full((200, 200, 3), 255, np.uint8)) < 0.5


def test_no_255_division():
    import inspect
    src = inspect.getsource(preprocess)
    assert "/ 255" not in src and "/255" not in src


def test_live_index_is_1():
    assert LIVE_INDEX == 1


def test_force_review_policy():
    for lv in [0.0, 0.3, 0.5, 0.7, 0.9, 1.0]:
        assert decide(lv, ModelStatus.HEURISTIC) == Decision.REVIEW
