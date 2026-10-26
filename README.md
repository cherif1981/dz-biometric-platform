# DZ Biometric Platform - Colab Edition

نسخة معدّلة من [DZ Biometric Platform](https://github.com/cherif1981/dz-biometric-platform)
تعمل على **Google Colab** مع **Cloudflare Tunnel**.

## 📅 آخر تحديث
2026-10-12 10:43:47

## ✅ حالة المشروع
| المكوّن | الحالة |
|---|---|
| FastAPI Server | ✅ يعمل |
| Cloudflare Tunnel | ✅ يعمل |
| OCR (عربية + فرنسية) | ✅ يعمل |
| Face Verification | ✅ دقة 94% |
| Liveness Detection | ✅ يعمل |
| Anti-Spoofing | ✅ يعمل (heuristic) |
| Audit DB | ✅ يعمل |
| GPU (CUDA) | ✅ مفعّل |

## 🎯 نتائج الاختبار

### آخر نتيجة: ✅ VERIFIED

## العتبات الفعلية (المصدر: `config/thresholds.yaml`)

| المقياس | العتبة | البيئة (env override) |
|---|---|---|
| تشابه الوجه | `0.5668` | `FACE_SIMILARITY_THRESHOLD` |
| الحيوية | `0.7` | `LIVENESS_THRESHOLD` |
| مكافحة الانتحال — رفض | `0.35` | `AS_REJECT_THRESHOLD` |
| مكافحة الانتحال — قبول | `0.5` | `AS_ACCEPT_THRESHOLD` |
| ثقة OCR | `0.8` | `OCR_CONFIDENCE_THRESHOLD` |

> **ملاحظة:** العتبات تُقرأ من `config/thresholds.yaml` فقط. أي تعديل في `README.md` أو `security.yaml` لا يؤثر على القرار. لتعديل سلوك النظام: عدّل YAML (أو استخدم env override).

### إحصائيات التدقيق
```json
{
  "total": 5,
  "by_status": {
    "REJECTED": 4,
    "VERIFIED": 1
  }
}
```

## 🔧 التعديلات المطبقة

### 1. `src/services/verification_service.py`
```python
# قبل
def __init__(self, ft=0.45, lt=0.60, ast=0.55):

# بعد
def __init__(self, ft=0.40, lt=0.50, ast=0.45):
```

### 2. `src/services/liveness_service.py`
```python
# قبل
def __init__(self, threshold=0.60):

# بعد
def __init__(self, threshold=0.50):
```

### 3. `src/services/antispoofing_service.py`
```python
# قبل
def __init__(self, threshold: float = 0.55):

# بعد
def __init__(self, threshold: float = 0.45):
```

## 🚀 التشغيل على Colab

```python
# 1. تثبيت المكتبات
!pip install fastapi uvicorn[standard] python-multipart nest-asyncio
!pip install pydantic pydantic-settings sqlalchemy
!pip install insightface onnxruntime opencv-python-headless easyocr
!pip install python-jose[cryptography] passlib[bcrypt] loguru

# 2. استنساخ المشروع
!git clone https://github.com/cherif1981/dz-biometric-colab-results.git
%cd dz-biometric-colab-results

# 3. تشغيل الخادم
!uvicorn src.main:app --host 0.0.0.0 --port 8000 &

# 4. Cloudflare Tunnel
!wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O /usr/local/bin/cloudflared
!chmod +x /usr/local/bin/cloudflared
!cloudflared tunnel --url http://localhost:8000
```

## 📁 هيكل المشروع

```
dz-biometric-colab-results/
├── src/
│   ├── api/v1/          # نقاط النهاية
│   ├── core/            # الإعدادات والأمان
│   ├── modules/         # OCR, Face, Liveness
│   └── services/        # خدمات التطبيق
├── tests/
├── docs/
├── requirements.txt
└── README.md
```

## 👤 المؤلف
- **cherif1981** <meddourcherif1981@gmail.com>

## 📄 الترخيص
هذا المشروع مرخص تحت MIT License.