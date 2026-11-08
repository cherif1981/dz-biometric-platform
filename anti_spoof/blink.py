"""كاشف رمشة — OpenCV Haar (يعمل على Python 3.13، بلا MediaPipe)."""
# ── Lazy cascade loading ──
# Loaded on first use to avoid import failure when cv2 lacks CascadeClassifier.
import threading as _threading

import cv2

_cascade_lock = _threading.Lock()
_cascade_cache = {}


def _get_cascade(name, xml):
    """Load (once) and return a cv2.CascadeClassifier for the given XML file."""
    if name in _cascade_cache:
        return _cascade_cache[name]
    with _cascade_lock:
        if name not in _cascade_cache:
            if not hasattr(cv2, "CascadeClassifier"):
                raise RuntimeError(
                    "cv2.CascadeClassifier missing - install opencv-python-headless "
                    "with objdetect support (or opencv-contrib-python)"
                )
            _cascade_cache[name] = cv2.CascadeClassifier(
                cv2.data.haarcascades + xml
            )
    return _cascade_cache[name]


def _get_face():
    return _get_cascade("face", "haarcascade_frontalface_default.xml")


def _get_eye():
    return _get_cascade("eye", "haarcascade_eye.xml")


_face = None

_face_lock = __import__("threading").Lock()



def _get_face_classifier():

    """Lazy init: avoids failing at import time if cv2 lacks CascadeClassifier."""

    global _face

    if _get_face_classifier() is not None:

        return _get_face_classifier()

    with _face_lock:

        if _get_face_classifier() is None:

            if not hasattr(cv2, "CascadeClassifier"):

                raise RuntimeError(

                    "cv2.CascadeClassifier missing — install opencv-python-headless "

                    "with objdetect support (or opencv-contrib-python)"

                )

            _face = cv2.CascadeClassifier(

                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"

            )

    return _get_face_classifier()
# [lazy] _eye = cv2.data.haarcascades + "haarcascade_eye.xml"  (moved to _get_cascade)
def _eyes_in_frame(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = _get_face_classifier().detectMultiScale(gray, 1.1, 5, minSize=(80, 80))
    if len(faces) == 0:
        return 0
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    return len(_get_eye().detectMultiScale(gray[y:y + h, x:x + w], 1.1, 6, minSize=(20, 20)))


def detect_blink(frames, min_open_frames=1):
    """يعيد (blinked: bool, history: list[int])."""
    counts = [_eyes_in_frame(f) for f in frames]
    if len(counts) < 4:
        return False, counts
    for i in range(1, len(counts) - 1):
        if (counts[i] == 0
                and counts[i - 1] >= min_open_frames
                and counts[i + 1] >= min_open_frames):
            return True, counts
    return False, counts
