from face.face_verification import verify_faces


def test_verify_faces_match():
    e = [0.1] * 128
    r = verify_faces(e, e, tolerance=0.6)
    assert r["match"] is True
    assert r["distance"] == 0.0
    assert r["confidence"] == 1.0


def test_verify_faces_no_match():
    e1 = [0.0] * 128
    e2 = [1.0] * 128
    r = verify_faces(e1, e2, tolerance=0.6)
    assert r["match"] is False
    assert r["distance"] > 0.6


def test_verify_faces_empty():
    r = verify_faces([], [1.0])
    assert r["match"] is False
    assert r["distance"] is None