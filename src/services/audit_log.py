"""تسجيل محاولات التحقق - للمراجعة الجنائية واليدوية."""

import json
import pathlib
import time
import uuid
from datetime import datetime, timezone

from loguru import logger

LOG_DIR = pathlib.Path("/content/dz-biometric-platform/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "verification_audit.jsonl"


def log_attempt(
    *,
    request_id: str | None = None,
    status: str,
    code: str | None = None,
    reason: str | None = None,
    antispoofing_score: float | None = None,
    similarity: float | None = None,
    detector: str | None = None,
    user_ref: str | None = None,  # معرف مستخدم مجزّأ (لا تخزّن بيانات شخصية)
    extra: dict | None = None,
) -> str:
    """
    يكتب سطرًا واحدًا بصيغة JSONL. لا يرمي استثناءات أبدًا (fail-safe).
    """
    rid = request_id or str(uuid.uuid4())
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "request_id": rid,
        "status": status,
        "code": code,
        "reason": reason,
        "antispoofing_score": antispoofing_score,
        "similarity": similarity,
        "detector": detector,
        "user_ref": user_ref,
    }
    if extra:
        record["extra"] = extra

    try:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.error(f"audit log write failed: {e}")

    if status == "REJECTED":
        logger.warning(
            f"[{rid}] REJECTED code={code} reason={reason} "
            f"score={antispoofing_score} similarity={similarity}"
        )
    return rid


def read_recent(n: int = 50) -> list[dict]:
    """قراءة آخر n محاولة للعرض/المراجعة."""
    if not LOG_FILE.exists():
        return []
    lines = LOG_FILE.read_text(encoding="utf-8").splitlines()
    out = []
    for line in lines[-n:]:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out
