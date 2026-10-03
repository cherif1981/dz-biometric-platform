"""فلتر logging لمنع تسريب البيانات الحساسة."""
import logging
import re
from typing import Optional


SENSITIVE_KEYS = [
    "face_encoding", "raw_text", "document_image",
    "nin", "password", "secret", "token", "access_token",
    "hashed_password", "biometric_encryption_key",
    "selfie", "face_image", "embedding",
]

_KEY_GROUP = "|".join(SENSITIVE_KEYS)

PATTERNS = [
    # JSON: "key": "value"
    re.compile(r'"(?:' + _KEY_GROUP + r')"\s*:\s*"[^"]*"', re.IGNORECASE),
    # JSON: "key": value
    re.compile(r'"(?:' + _KEY_GROUP + r')"\s*:\s*[^,}\]]+', re.IGNORECASE),
    # key='value' أو key="value"
    re.compile(r"\b(?:" + _KEY_GROUP + r")\s*=\s*(?:'[^']*'|\"[^\"]*\")", re.IGNORECASE),
    # key=value
    re.compile(r"\b(?:" + _KEY_GROUP + r")\s*=\s*\S+", re.IGNORECASE),
    # key: value
    re.compile(r"\b(?:" + _KEY_GROUP + r")\s*:\s*\S+", re.IGNORECASE),
]


def _redact(text: str) -> str:
    """يستبدل كل القيم الحساسة في نص."""
    if not text:
        return text
    for pattern in PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text


class SensitiveDataFilter(logging.Filter):
    """يستبدل البيانات الحساسة بـ[REDACTED]."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            # اجمع الرسالة الكاملة
            msg = record.getMessage()
            redacted = _redact(msg)
            if redacted != msg:
                record.msg = redacted
                record.args = ()
        except Exception:
            pass
        return True


def install_sensitive_filter(logger: Optional[logging.Logger] = None):
    """
    ثبّت الفلتر على logger معيّن أو على root + كل handlers الحالية.
    """
    target = logger or logging.getLogger()

    # على الـlogger نفسه
    if not any(isinstance(f, SensitiveDataFilter) for f in target.filters):
        target.addFilter(SensitiveDataFilter())

    # على كل handlers
    for handler in target.handlers:
        if not any(isinstance(f, SensitiveDataFilter) for f in handler.filters):
            handler.addFilter(SensitiveDataFilter())


# ثبّت عند الاستيراد
install_sensitive_filter()
