"""كاشف رمشة — OpenCV Haar (يعمل على Python 3.13، بلا MediaPipe)."""
import cv2

_face = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
_eye = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")


def _eyes_in_frame(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = _face.detectMultiScale(gray, 1.1, 5, minSize=(80, 80))
    if len(faces) == 0:
        return 0
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    return len(_eye.detectMultiScale(gray[y:y + h, x:x + w], 1.1, 6, minSize=(20, 20)))


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
