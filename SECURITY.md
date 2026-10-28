# Security Model — dz-biometric-platform

هذا المستند يعدد الضوابط الأمنية، كيف تُنفّذ، وكيف تُختبر. الضابط
يُعتبر "مُثبتًا" فقط إذا نجح اختباره في `tests/test_security.py`.

## نموذج التهديد
- **عميل خبيث**: يستطيع إرسال أي حمولة، إعادة استخدام جلسات، تزوير
  درجات، تعديل إيصالات، أو استدعاء نقاط خارج الترتيب.
- **نموذج PAD معطوب**: قد يرمي استثناءً أو يعيد درجة منخفضة.
- **بنية تحتية مخترقة**: قاعدة التدقيق قد تصبح غير متاحة، أو قد
  يصل مهاجم إلى الملف مباشرة.
- **طلبات متزامنة**: قد يصل طلبان لجلسة واحدة في نفس اللحظة.

## الضوابط

### 1. القرار على الخادم
درجة الحيوية تُحسب في `run_pad`. لا يُقرأ `client_pad_score`. الإيصال
موقّع HMAC على (`job_id`, `nonce`, `decision`, `score`).

اختبار: `test_forged_score_ignored`, `test_replay_rejected`.

### 2. آلة حالات fail-closed
الانتقالات صريحة؛ الانتقال غير المصرّح يرفع `StateErr`. الحالات
الطرفية (`PAD_FAILED`, `ACCEPTED`, `REJECTED`, `TERMINATED`) نهائية.

اختبار: `test_illegal_transition_blocked`.

### 3. منع TOCTOU
أول انتقال (`CHALLENGE_ISSUED → PAD_EVALUATING`) ذري عبر Redis
`WATCH/MULTI`. الطلبات المتزامنة: واحد ينجح، الباقي 409.

اختبار: `test_concurrent_submit_only_one_succeeds`.

### 4. التدقيق هو نقطة الالتزام
`ACCEPTED` لا تُكتب في Redis قبل كتابة سجل التدقيق. إن فشل التدقيق:
الجلسة `TERMINATED` والعميل يستلم 500 بدون إيصال. لا قرار بدون سجل.

اختبار: `test_phantom_decision_prevented`.

### 5. سلامة سلسلة التدقيق
`row_hash = sha256(prev_hash || sha256(payload))`. أي تعديل يكسر
السلسلة، و`verify_chain()` يحدد السطر المكسور.

اختبار: `test_chain_detects_tampering`.

### 6. التدقيق append-only
SQLite: triggers تمنع `UPDATE`/`DELETE`. PostgreSQL: دور
`audit_writer` بـ `INSERT` فقط.

اختبار: `test_audit_append_only_triggers`.

### 7. تحديد معدل موزّع
`slowapi` يستخدم Redis كـ `storage_uri`. بدون `REDIS_URL`،
ينتقل إلى `memory://` — غير آمن لتعدد النسخ.

اختبار: يدوي عبر نسختين — انظر `README`.

### 8. مراقبة مستمرة
`monitor_runner.py` يستطلع `verify_chain()` كل `MONITOR_INTERVAL`.
عند التلاعب: تنبيه (webhook + بريد) ثم exit 2 — يلتقطه systemd.

## قيود معروفة
- **احتياطي HMAC_SECRET**: `dz_service.py` يستخدم `"dev-secret"` إن
  لم يُضبط `HMAC_SECRET`. **ممنوع في الإنتاج.** استخدم مدير أسرار.
- **لا انتهاء صلاحية للإيصال**: الإيصالات صالحة للأبد. أضف `exp`.
- **429 من slowapi غير مسجل في التدقيق**: قرار متعمد (ليس قرارًا
  بيومتريًا). في الإنتاج، سجّله في سجل أمني منفصل.

## قائمة تحقق قبل الإنتاج
- [ ] `HMAC_SECRET` من مدير أسرار، لا من الكود.
- [ ] `REDIS_URL` بـ `rediss://` (TLS).
- [ ] `AUDIT_DB_URL` PostgreSQL بدور `INSERT` فقط على `audit_logs`.
- [ ] `AUDIT_DB_URL_RO` بدور `SELECT` فقط لـ `verify_chain()`.
- [ ] `monitor_runner.py` تحت systemd بمستخدم `audit-mon`.
- [ ] Cloudflare Access يحمي المسارات الإدارية.
- [ ] `docs_url=None`, `openapi_url=None` في الإنتاج.
- [ ] CORS origins صريحة، لا `["*"]`.
- [ ] اختبار اختراق مستقل على staging.
- [ ] سياسة احتفاظ/حذف موثقة ومطبقة.

## الإبلاغ عن الثغرات
استخدم GitHub Security Advisories، أو راسل
meddourcherif1981@gmail.com. لا تفتح issue علنيًا.
