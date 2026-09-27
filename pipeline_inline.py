"""
Pipeline داخلي — OCR + Face Verification + Liveness
مأخوذ من المرحلة 2، جاهز للاستيراد من api.py
"""
import cv2, uuid, re, os
from datetime import datetime, timezone
import numpy as np
import easyocr
from insightface.app import FaceAnalysis
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# ── تهيئة عالمية (تتم مرة واحدة) ──
print("Initializing pipeline components...")

reader = easyocr.Reader(['ar', 'en'], gpu=True)
print("✅ EasyOCR loaded")

app_face = FaceAnalysis(
    name='buffalo_l',
    providers=['CUDAExecutionProvider', 'CPUExecutionProvider']
)
app_face.prepare(ctx_id=0, det_size=(640, 640))
print("✅ InsightFace loaded")

MODEL_PATH = "face_landmarker.task"
if not os.path.exists(MODEL_PATH):
    import urllib.request
    url = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
    urllib.request.urlretrieve(url, MODEL_PATH)

base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
lm_options = vision.FaceLandmarkerOptions(
    base_options=base_options,
    output_face_blendshapes=True,
    num_faces=1
)
landmarker = vision.FaceLandmarker.create_from_options(lm_options)
print("✅ MediaPipe loaded")


# ── OCR + Field Extraction ──
def extract_fields_from_ocr(ocr_results):
    full_text = " ".join([t for _, t, _ in ocr_results])
    fields = {
        "raw_text": full_text,
        "national_id": None,
        "id_number": None,
        "issue_date": None,
        "expiry_date": None,
        "birth_date": None,
        "last_name": None,
        "first_name": None,
        "gender": None,
        "place_of_birth": None,
        "issuing_authority": None
    }
    m = re.search(r'\b\d{18}\b', full_text)
    if m: fields["national_id"] = m.group()
    m = re.search(r'\b\d{9}\b', full_text)
    if m: fields["id_number"] = m.group()
    dates = re.findall(r'\b\d{4}[./]\d{2}[./]\d{2}\b', full_text)
    if len(dates) >= 1: fields["issue_date"] = dates[0]
    if len(dates) >= 2: fields["expiry_date"] = dates[1]
    if len(dates) >= 3: fields["birth_date"] = dates[2]
    if any(k in full_text for k in ['ذكر', ' M ', 'Male']):
        fields["gender"] = "M"
    elif any(k in full_text for k in ['أنثى', ' F ', 'Female']):
        fields["gender"] = "F"
    return fields


def run_ocr(image_path):
    raw = reader.readtext(image_path, detail=1)
    fields = extract_fields_from_ocr(raw)
    fields["ocr_confidence"] = round(
        float(np.mean([c for _, _, c in raw])) if raw else 0.0, 3
    )
    return fields


# ── Face Verification ──
def _largest_face(faces):
    return max(faces, key=lambda f: (f.bbox[2]-f.bbox[0])*(f.bbox[3]-f.bbox[1]))


def extract_embedding(image_path):
    img = cv2.imread(image_path)
    if img is None:
        return None, "cannot_read_image"
    faces = app_face.get(img)
    if not faces:
        return None, "no_face_detected"
    f = _largest_face(faces)
    return f.embedding, None


def cosine_similarity(a, b):
    a = a / np.linalg.norm(a)
    b = b / np.linalg.norm(b)
    return float(np.dot(a, b))


def run_face_verification(id_card_path, selfie_path, threshold=0.35):
    emb_id, err1 = extract_embedding(id_card_path)
    emb_selfie, err2 = extract_embedding(selfie_path)
    if err1 or err2:
        return {"verified": False, "error": err1 or err2, "similarity": None}
    sim = cosine_similarity(emb_id, emb_selfie)
    return {
        "verified": sim >= threshold,
        "similarity": round(sim, 4),
        "threshold": threshold,
        "confidence": "high" if sim > 0.5 else "medium" if sim > 0.35 else "low"
    }


# ── Liveness ──
def run_liveness(selfie_path):
    mp_image = mp.Image.create_from_file(selfie_path)
    result = landmarker.detect(mp_image)
    if not result.face_landmarks:
        return {"passed": False, "error": "no_face_detected"}
    blendshapes = {}
    if result.face_blendshapes:
        for bs in result.face_blendshapes[0]:
            blendshapes[bs.category_name] = bs.score
    blink_left = blendshapes.get("eyeBlinkLeft", 0.0)
    blink_right = blendshapes.get("eyeBlinkRight", 0.0)
    jaw_open = blendshapes.get("jawOpen", 0.0)
    blink = (blink_left > 0.5) or (blink_right > 0.5)
    jaw = jaw_open > 0.4
    return {
        "passed": blink or jaw,
        "blink_detected": blink,
        "jaw_open_detected": jaw,
        "metrics": {
            "eyeBlinkLeft": round(blink_left, 3),
            "eyeBlinkRight": round(blink_right, 3),
            "jawOpen": round(jaw_open, 3)
        }
    }


# ── Pipeline الرئيسي ──
def verify_identity(id_card_path, selfie_path,
                    face_threshold=0.35,
                    require_liveness=True):
    verification_id = str(uuid.uuid4())
    start = datetime.now(timezone.utc)

    result = {
        "verification_id": verification_id,
        "timestamp": start.isoformat(),
        "input": {"id_card": id_card_path, "selfie": selfie_path},
        "ocr": {},
        "face": {},
        "liveness": {},
        "status": "processing",
        "processing_time_ms": 0
    }

    try:
        result["ocr"] = run_ocr(id_card_path)
    except Exception as e:
        result["ocr"] = {"error": str(e)}

    try:
        result["face"] = run_face_verification(
            id_card_path, selfie_path, threshold=face_threshold
        )
    except Exception as e:
        result["face"] = {"error": str(e), "verified": False}

    try:
        result["liveness"] = run_liveness(selfie_path)
    except Exception as e:
        result["liveness"] = {"error": str(e), "passed": False}

    face_ok = result["face"].get("verified", False)
    liveness_ok = result["liveness"].get("passed", False)

    if face_ok and (liveness_ok or not require_liveness):
        result["status"] = "verified"
    elif not face_ok:
        result["status"] = "rejected_face_mismatch"
    elif require_liveness and not liveness_ok:
        result["status"] = "rejected_liveness_failed"
    else:
        result["status"] = "rejected"

    elapsed = (datetime.now(timezone.utc) - start).total_seconds() * 1000
    result["processing_time_ms"] = round(elapsed, 2)
    return result
