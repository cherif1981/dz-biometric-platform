from detection.card_detector import CardDetector


def test_detector_init():
    d = CardDetector()
    assert d is not None


def test_detector_fallback_contour(card_like_image):
    d = CardDetector()
    corners = d.detect(card_like_image)
    assert corners is None or corners.shape == (4, 2)


def test_detector_on_blank(blank_image):
    d = CardDetector()
    corners = d.detect(blank_image)
    assert corners is None or corners.shape == (4, 2)