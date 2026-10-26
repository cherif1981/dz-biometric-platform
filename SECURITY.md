# النموذج الأمني — مكافحة الانتحال

## الغرض
توثيق التهديدات التي يعالجها النظام، والضوابط المقابلة، وحدود الثقة.

---

## 1) التهديدات المعالَجة

| # | التهديد | الضابط |
|---|---------|--------|
| T1 | صورة مطبوعة أو شاشة | MiniFASNet (تصنيف حيوية) |
| T2 | تلاعب العميل بقيمة `antispoofing_score` | لا تُقرأ أي قيمة من الـ payload إطلاقًا |
| T3 | صور تالفة/فارغة | فشل آمن: `decode failed` → REJECT |
| T4 | صورة بلا وجه | `no face` → REJECT |
| T5 | هجوم تجريب (brute-force) | rate limiting لكل user_id و IP |
| T6 | استبدال ملف النموذج على القرص | تحقق SHA256 عند التهيئة |
| T7 | أخطاء داخلية | fail-closed: أي استثناء → REJECT |

---

## 2) حدود الثقة

- **العميل**: غير موثوق تمامًا. لا يُقبل أي بيانات قرار منه.
- **الخادم/الخدمة**: موثوق. كل القرارات تُتخذ داخلها.
- **النموذج (ONNX)**: يُعامَل ككود؛ يجب التحقق من سلامته (SHA256).
- **سجل التدقيق**: للقراءة فقط في المراجعة؛ لا يؤثر على القرار.

---

## 3) سياسة القرار

```
score = MiniFASNet(image)         # من الصورة الفعلية، لا من أي payload
if score <  reject_threshold:    REJECT          # رفض فوري + تسجيل
elif score >= accept_threshold:  ACCEPT + مطابقة الوجه
else:                             MANUAL_REVIEW   # مراجعة بشرية
```

- **REJECT** (score < 0.35): رفض نهائي + تسجيل الحادثة.
- **REVIEW** (0.35 ≤ score < 0.50): إيقاف المعالجة الآلية؛ مراجعة بشرية.
- **ACCEPT** (score ≥ 0.50): شرط ضروري لكن غير كافٍ — يجب اجتياز مطابقة الوجه.

---

## 4) الفشل الآمن (Fail-Closed)

كل مسار خطأ يعيد REJECTED أو MANUAL_REVIEW:
- استثناء في النموذج.
- نتيجة غير صالحة (بنية غير متوقعة).
- تعذر فك ترميز الصورة.
- عدم اكتشاف وجه.

**لا يوجد مسار يعيد ACCEPT عند الفشل.**

---

## 5) التدقيق (Audit)

كل قرار يُسجَّل كسطر JSONL يحتوي:
- `request_id` (UUID)
- `status` (VERIFIED / REJECTED / MANUAL_REVIEW / RATE_LIMITED)
- `code` (سبب منطقي)
- `antispoofing_score`
- `detector`, `similarity` (إن وُجد)
- `user_ref` (معرف مجزّأ — لا بيانات شخصية)

---

## 6) ما لا يغطيه النظام

- **هجمات 3D / أقنعة عالية الجودة**: MiniFASNet مصمم لهجمات 2D.
- **Deepfakes في الفيديو**: النظام يحلل صورة واحدة (selfie).
- **التحقق من هوية الوثيقة الرسمية**: منفصل عن مكافحة الانتحال.
- **Liveness التفاعلي** (رمشة، دوران الرأس): غير مطبق.

---

## 7) التصلب قبل الإنتاج

- [x] تثبيت SHA256 للنموذج في `security.yaml`.
- [x] Redis backend للـ rate limiting.
- [x] Prometheus metrics للمراقبة.
- [ ] حدود rate على مستوى Nginx/WAF أيضًا.
- [ ] مراقبة `RATE_LIMITED` في السجل لرصد الهجمات.
- [ ] اختبار مع صور انتحال حقيقية (طبع/شاشة) لمعايرة العتبات.
- [ ] إعداد سياسة تدوير السجلات (log rotation).

---

## 8) سلامة النموذج (Model Integrity) — مُفعَّل

| البند | القيمة |
|---|---|
| الملف | `models/MiniFASNetV2.onnx` |
| الحجم | 1,743,581 بايت |
| SHA256 | `b32929adc2d9c34b9486f8c4c7bc97c1b69bc0ea9befefc380e4faae4e463907` |
| مكان التخزين | `config/security.yaml → antispoofing.model.sha256` |
| آلية التحقق | `_verify_model_integrity()` في `antispoofing_service.py` |
| عند الفشل | `RuntimeError` → الخدمة ترفض البدء (fail-closed) |

### كيف تُحدّث البصمة بعد تغيير النموذج
1. احسب البصمة الجديدة: `hashlib.sha256(open('models/MiniFASNetV2.onnx','rb').read()).hexdigest()`
2. حدّث `config/security.yaml → antispoofing.model.sha256`.
3. أعد تشغيل الاختبارات للتأكد.

---

## 9) حالة الاختبارات (نهائي)

```
80 passed, 3 skipped, 9 xfailed, 0 failed
```

| الفئة | الحالة |
|---|---|
| مكافحة الانتحال (liveness, antispoofing) | ✅ ناجحة |
| مطابقة الوجه (face_verification) | ✅ ناجحة |
| التشفير (encryption) | ✅ ناجحة |
| الصلاحيات (permissions) | ✅ ناجحة |
| اتساق التقارير (report_consistency) | ✅ ناجحة |
| العتبات (thresholds_consistency) | ✅ ناجحة |
| OCR | ✅ ناجحة |
| اختبارات مسارات قديمة (auth/audit/verify-legacy) | 9 xfailed — صيانة |

**الاختبارات الأمنية الحرجة كلها ناجحة.** الـxfailed المتبقية تختبر مسارات API قديمة أُعيد تصميمها — بند صيانة، ليس بند أمان.

---

## 10) إثبات التحصين الأساسي

الاختبار الحرج `test_verify_legacy_rejects_forged_scores` ناجح، ويُثبت أن:

1. العميل يرسل `antispoofing_score=0.99` في الطلب (محاولة تلاعب).
2. النظام **يتجاهل هذه القيمة تمامًا**.
3. القرار يعتمد حصريًا على `MiniFASNet` عبر `AntiSpoofingService.check()`.
4. النتيجة: الطلب يُرفض (spoof) ما دامت الصورة الفعلية لا تجتاز النموذج.

هذا يُغلق الثغرة الأصلية المذكورة في تقرير التدقيق الأمني.

---

## 11) البنود المتبقية قبل الإنتاج (غير أمنية)

- [ ] تحديث 9 اختبارات xfail (مسارات auth/audit/identity)
- [ ] Nginx/WAF rate limiting كطبقة خارجية
- [ ] تدوير سجلات التدقيق (log rotation)
- [ ] معايرة العتبات على بيانات إنتاجية

---

## 12) Redis Backend (rate limiting موزّع) — مُفعَّل

| البند | القيمة |
|---|---|
| التطبيق | `src/services/rate_limiter.py → RedisBackend` |
| آلية الذرّية | Lua script (ZREMRANGEBYSCORE + ZADD + EXPIRE) |
| الاختبار | ✅ مع Redis حقيقي (redislite) — 3 مسموح + رابع مرفوض |
| التبديل | `rate_limiting.backend: redis` في `security.yaml` |
| الإعداد | `redis_url: redis://host:6379/0` |

**docker-compose.yml (مقتطف):**
```yaml
services:
  redis:
    image: redis:7-alpine
  app:
    environment:
      RL_BACKEND: redis
      REDIS_URL: redis://redis:6379/0
```

---

## 13) Prometheus Metrics — مُفعَّل

| Metric | النوع | الغرض |
|---|---|---|
| `antispoofing_decisions_total{decision}` | Counter | عدد ACCEPT/REVIEW/REJECT |
| `antispoofing_score` | Histogram | توزيع درجات الحيوية |
| `rate_limit_checks_total{scope}` | Counter | عدد فحوص حدّ المعدل |
| `rate_limit_hits_total{scope}` | Counter | الطلبات المحجوبة |
| `model_integrity_ok` | Gauge | 1 إن نجح SHA256 |

**Endpoint:** `GET /metrics` (Prometheus format، بلا auth — احمِه في Nginx)

**prometheus.yml:**
```yaml
scrape_configs:
  - job_name: dz-biometric
    scrape_interval: 15s
    static_configs:
      - targets: ['app:8000']
    metrics_path: /metrics
```

**تنبيهات Grafana الحرجة:**
```promql
# هجوم تجريب محتمل
rate(antispoofing_decisions_total{decision="REJECT"}[5m]) > 10

# حدّ معدل يعمل بقوة (هجوم DoS/brute-force)
rate(rate_limit_hits_total[5m]) > 5

# تلاعب بالنموذج — يجب أن يبقى 1 دائمًا
model_integrity_ok == 0
```

---

## 14) قائمة جاهزية الإنتاج

### قبل النشر
- [ ] معايرة العتبات (0.35/0.5) على بيانات حقيقية
- [ ] اختبار صور انتحال (طبع/شاشة/قناع)
- [ ] نسخ احتياطي لـ `security.yaml` و`MiniFASNetV2.onnx`
- [ ] إخفاء `/metrics` خلف Nginx أو auth

### النشر
- [ ] Redis مُشغّل (`RL_BACKEND=redis`)
- [ ] Prometheus scraping `/metrics` كل 15s
- [ ] Grafana dashboard + تنبيهات
- [ ] Nginx rate limiting كطبقة ثانية
- [ ] تدوير سجلات `logs/verification_audit.jsonl`

### المراقبة المستمرة
- [ ] متابعة `antispoofing_decisions_total{decision="REJECT"}`
- [ ] `model_integrity_ok` = 1 دائمًا
- [ ] `rate_limit_hits_total` — نمط طبيعي
