# Threat Model — STRIDE

**النطاق:** DZ Biometric Platform API
**آخر تحديث:** 2026-01-01

## 1. الأصول

| الأصل | الحساسية | التأثير |
|---|---|---|
| صور وثائق | عالية جدًا | سرقة هوية |
| قوالب بيومترية | عالية جدًا | انتحال دائم |
| مفاتيح تشفير | حرجة | كشف الكل |
| سجلات تدقيق | متوسطة | فقدان مساءلة |

## 2. STRIDE

### S — Spoofing
- صور مزيفة → liveness + antispoof + challenge.
- انتحال JWT → HS256 + exp + type.
- انتحال خدمة → mTLS (P3).

### T — Tampering
- استبدال نموذج → SHA-256 manifest + verify_model.
- تعديل DB → تشفير + audit log immutable.

### R — Repudiation
- إنكار طلب → audit.jsonl (timestamp + IP + user_id).
- إنكار قرار بشري → reviewer_id + decided_at.

### I — Information Disclosure
- تسريب صور → لا نسجّل bytes، فقط hashes.
- قوالب مسروقة → AES-256-GCM بمفتاح منفصل.
- تفاصيل أخطاء → error handler عام.

### D — Denial of Service
- إغراق /verify/ → slowapi 10/min/IP.
- إغراق /auth/login → rate limit + bcrypt.
- payload كبير → max_upload_size (10 MB).

### E — Elevation of Privilege
- طلب admin → RequireScopes + JWT.
- IDOR على review/{id} → ownership (P3).
- demo bypass → DEBUG=true فقط.

## 3. أعلى 3 مخاطر (DREAD)

| # | التهديد | Total |
|---|---|---|
| 1 | deepfake presentation attack | 36 |
| 2 | تسريب قوالب بيومترية | 36 |
| 3 | JWT مسروق | 32 |

**المعالجات:**
1. تحديث antispoof + benchmark ربع سنوي.
2. تدوير مفاتيح + HSM (P3).
3. jti + blacklist + refresh rotation.

## 4. الضوابط المفعلة

- JWT مع انتهاء
- RequireScopes على كل مسار
- slowapi rate limiting
- AES-256-GCM للقوالب
- SHA-256 للنماذج
- audit.jsonl منظم
- /ready مع فحص DB
- demo مقيّد بـ DEBUG
- Docker non-root
