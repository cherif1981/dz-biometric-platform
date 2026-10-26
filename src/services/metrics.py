"""مقاييس Prometheus — idempotent (آمنة عند إعادة الاستيراد)."""
from prometheus_client import REGISTRY, Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST


def _unregister_if_exists(*names: str) -> None:
    """يحذف أي collector مسجّل سابقًا بنفس الاسم (يمنع DuplicateTimeseries)."""
    for name in names:
        collector = REGISTRY._names_to_collectors.get(name)
        if collector is not None:
            try:
                REGISTRY.unregister(collector)
            except Exception:
                pass


# تنظيف أي تسجيل سابق (Colab/التطوير: وحدات تُعاد استيرادها)
_unregister_if_exists(
    "antispoofing_decisions_total",
    "antispoofing_score",
    "rate_limit_hits_total",
    "rate_limit_checks_total",
    "model_integrity_ok",
)

# ── مكافحة الانتحال ──
ANTISPOOF_TOTAL = Counter(
    "antispoofing_decisions_total",
    "عدد قرارات مكافحة الانتحال",
    ["decision"],
)
ANTISPOOF_SCORE = Histogram(
    "antispoofing_score",
    "توزيع درجات الحيوية",
    buckets=[0.1, 0.2, 0.3, 0.35, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.99, 1.0],
)

# ── حدّ المعدل ──
RATE_LIMIT_HITS = Counter(
    "rate_limit_hits_total",
    "طلبات تجاوزت حدّ المعدل",
    ["scope"],
)
RATE_LIMIT_CHECKS = Counter(
    "rate_limit_checks_total",
    "عدد فحوص حدّ المعدل",
    ["scope"],
)

# ── سلامة النموذج ──
MODEL_INTEGRITY_OK = Gauge(
    "model_integrity_ok",
    "1 إن نجح SHA256، 0 إن فشل",
)


def record_antispoof_result(decision: str, score: float) -> None:
    try:
        ANTISPOOF_TOTAL.labels(decision=decision).inc()
        ANTISPOOF_SCORE.observe(max(0.0, min(1.0, float(score))))
    except Exception:
        pass


def record_rate_limit(scope: str, blocked: bool) -> None:
    try:
        RATE_LIMIT_CHECKS.labels(scope=scope).inc()
        if blocked:
            RATE_LIMIT_HITS.labels(scope=scope).inc()
    except Exception:
        pass


def set_model_integrity(ok: bool) -> None:
    try:
        MODEL_INTEGRITY_OK.set(1 if ok else 0)
    except Exception:
        pass


def metrics_payload():
    return generate_latest(), CONTENT_TYPE_LATEST
