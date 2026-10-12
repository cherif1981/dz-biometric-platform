import numpy as np
from src.modules.face_verification.matcher import FaceMatcher


def test_same_embedding_matches():
    v = np.random.rand(512).astype(np.float32)
    m = FaceMatcher(threshold=0.5)
    r = m.compare(v, v)
    assert r["match"] is True
    assert r["similarity"] > 0.99


def test_orthogonal_no_match():
    a = np.zeros(512, dtype=np.float32); a[0] = 1.0
    b = np.zeros(512, dtype=np.float32); b[1] = 1.0
    m = FaceMatcher(threshold=0.5)
    assert m.compare(a, b)["match"] is False


def test_missing_embedding():
    assert FaceMatcher().compare(None, None)["match"] is False