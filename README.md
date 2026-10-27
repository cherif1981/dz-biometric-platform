# DZ Biometric Platform - Colab Edition

نسخة معدّلة تعمل على Google Colab مع Cloudflare Tunnel.

**آخر تحديث:** 2026-10-27 (تقييم موثّق)

---

## ⚠️ إفصاح مهم

الادعاء السابق **«دقة 94%»** لم يكن قابلاً لإعادة الإنتاج.
استُبدل بتقييم مستقل على LFW.

---

## ✅ حالة المشروع

| المكوّن | الحالة |
|---|---|
| FastAPI | ✅ يعمل |
| Cloudflare Tunnel | ✅ يعمل |
| **Face Verification** | ✅ **EER 4.07%** |
| OCR | ⚠️ لم يُقيَّم |
| Liveness | ⚠️ لم يُقيَّم |
| **Anti-Spoofing** | ❌ **نموذج منحلّ** |
| Audit DB | ✅ يعمل |

---

## 📊 تقييم مطابقة الوجه — insightface على LFW

| المقياس | القيمة |
|---|---|
| **EER** | **4.07%** |
| ROC-AUC | 0.9753 |
| FAR @ EER | 4.27% |
| FRR @ EER | 3.88% |
| معدل فشل الكشف | **18.0%** |
| العينة | 129+117 |

**إعادة الإنتاج:**

- LFW (150+150) عبر sklearn
- البذرة: 42 في `eval_scores_face.json`
- padding=60 عند فشل الكشف

**إفصاحات:**

1. تحيّز انتقائي: 4.07% تخص 246/300 فقط.
2. 117 سلبية → أدنى FMR = 8.5×10⁻³.
3. فضاء cosine خام؛ الإنتاج يحوّل بـ (cos+1)/2.

---

## مكافحة الانتحال — **لم تُقيَّم**

MiniFASNetV2.onnx لا يستجيب للمحتوى:

| المدخل | probs[real] |
|---|---|
| أسود | 0.992 |
| أبيض | 0.995 |
| ضوضاء | 0.992 |
| حقيقي | 0.994 |
| هجوم | 0.993 |

الفرق: **0.001** — أقل من ضوضاء القياس.
لا APCER/BPCER. **المطلوب:** DeepPixBiS / CDCN / نموذج HuggingFace.

## OCR — **لم يُقيَّم**

يتطلب وثائق بنصوص مرجعية. غير متوفرة علناً.

---

## 🔧 العتبات (`config/thresholds.yaml`)

| المقياس | العتبة |
|---|---|
| تشابه الوجه | 0.5668 |
| الحيوية | 0.7 |
| AS — قبول | 0.5 |
| OCR | 0.8 |

> ⚠️ عتبة AS معطّلة — النموذج يُرجع ~0.99 للكل.

---

## 🔧 التعديلات المطبقة

### 1. ترتيب DocumentAI/OCRService

`self.ocr = OCRService()` قبل `DocumentAI(ocr_service=self.ocr)`.

### 2. face_service.py — استبدال stub بـ insightface

الـ stub القديم كان يُرجع 0.0 دائماً. الآن:

```python
# قبل
def verify(self, payload):
    return {self.modality: float(payload.get('face_score', 0.0))}

# بعد
class FaceVerificationService:
    def _embed(self, img):
        # insightface + padding=60/80
        return faces[0].normed_embedding
```

### 3. decision_policy.py — محرك قرار موحّد

`core/decision_engine.py` و `modules/ai/decision_engine.py`
أصبحا واجهتا تفويض إلى `UnifiedDecisionEngine`.
العتبات موحّدة مع لقطة في كل قرار.

---

## 🚀 التشغيل على Colab

```bash
!pip install fastapi uvicorn insightface onnxruntime easyocr
!git clone https://github.com/cherif1981/dz-biometric-colab-results.git
%cd dz-biometric-colab-results
!uvicorn src.main:app --host 0.0.0.0 --port 8000 &
!cloudflared tunnel --url http://localhost:8000
```

---

## 📁 الهيكل

```
src/api/v1/  src/core/  src/modules/  src/services/
config/thresholds.yaml
eval_scores_face.json
```

---

## 📋 سجل التغييرات

### 2026-10-27
- إصلاح DocumentAI/OCRService
- استبدال face stub بـ insightface
- توحيد محرك القرار
- EER 4.07% موثّق
- PAD: نموذج منحلّ موثَّق
- إزالة 94% غير القابل للتحقق

## 👤 المؤلف

**cherif1981** — meddourcherif1981@gmail.com

## 📄 الترخيص

MIT License.
