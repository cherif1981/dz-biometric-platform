import numpy as np

from preprocessing.resize import resize_image
from preprocessing.denoise import denoise_image
from preprocessing.contrast import enhance_contrast
from preprocessing.perspective import correct_perspective


def test_resize_image_keeps_ratio(blank_image):
    out = resize_image(blank_image, target_width=300)
    assert out.shape[1] == 300
    assert out.shape[0] == int(400 * (300 / 600))


def test_resize_noop_when_same_width(blank_image):
    out = resize_image(blank_image, target_width=600)
    assert out.shape == blank_image.shape


def test_denoise_returns_same_shape(noisy_image):
    out = denoise_image(noisy_image)
    assert out.shape == noisy_image.shape


def test_enhance_contrast_same_shape(blank_image):
    out = enhance_contrast(blank_image)
    assert out.shape == blank_image.shape


def test_correct_perspective():
    img = np.zeros((500, 500, 3), dtype=np.uint8)
    corners = np.array([[50, 50], [450, 50], [450, 450], [50, 450]], dtype=np.float32)
    out = correct_perspective(img, corners)
    assert out.shape[0] > 0 and out.shape[1] > 0