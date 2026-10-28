"""Regression guard against reintroducing the [0,1] bug."""
import numpy as np
import pytest
import onnxruntime as ort

from anti_spoof.preprocess import preprocess, liveness_from_output, LIVE_INDEX
from anti_spoof.decision import decide, ModelStatus, Decision

MODEL = "MiniFASNetV2.onnx"


@pytest.fixture(scope="module")
def session():
    return ort.InferenceSession(MODEL, providers=["CPUExecutionProvider"])


def _score(s, im):
    out = s.run(None, {"input": preprocess(im)})[0][0]
    return liveness_from_output(out)


def test_black_rejected(session):
    assert _score(session, np.zeros((200, 200, 3), np.uint8)) < 0.1


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
