"""Fixtures for AI tests: synthetic images."""
import cv2
import numpy as np
import pytest


@pytest.fixture
def blank_image() -> np.ndarray:
    return np.full((400, 600, 3), 255, dtype=np.uint8)


@pytest.fixture
def noisy_image() -> np.ndarray:
    img = np.random.randint(0, 255, (400, 600, 3), dtype=np.uint8)
    return img


@pytest.fixture
def card_like_image() -> np.ndarray:
    """White card on dark background."""
    img = np.zeros((600, 800, 3), dtype=np.uint8)
    cv2.rectangle(img, (100, 150), (700, 450), (255, 255, 255), -1)
    return img


@pytest.fixture
def text_image() -> np.ndarray:
    img = np.full((100, 400, 3), 255, dtype=np.uint8)
    cv2.putText(img, "123456789012345678", (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
    return img