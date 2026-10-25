"""Redaction utilities for logging PII (GDPR / BIPA compliance).

The audit finding: "settings for encryption keys do not by themselves
prove that all sensitive data is actually protected" applies to logs too.
"""

import hashlib
import re
from typing import Optional

_HEX_LIKE = re.compile(r"\b[0-9a-f]{32,}\b", re.IGNORECASE)
_B64_LIKE = re.compile(r"\b[A-Za-z0-9+/]{40,}={0,2}\b")


def mask_subject(subject_id: Optional[str]) -> str:
    """Return a stable short hash of subject_id (for correlation without exposure)."""
    if not subject_id:
        return "<none>"
    h = hashlib.sha256(str(subject_id).encode()).hexdigest()[:8]
    return f"<subject:{h}>"


def redact_message(msg: str) -> str:
    """Redact hex/base64-like blobs and obvious image markers.

    Handles both forms that may appear in logs:
      - Escaped literal:  '\\xff\\xd8\\xff'  (what repr(bytes) shows)
      - Actual bytes:     '\xff\xd8\xff'        (after latin-1 decode)
    """
    if not msg:
        return msg
    msg = _HEX_LIKE.sub("<REDACTED_HEX>", msg)
    msg = _B64_LIKE.sub("<REDACTED_B64>", msg)
    # JPEG magic — both forms
    msg = msg.replace(r"\xff\xd8\xff", "<REDACTED_JPEG>")
    msg = msg.replace("\xff\xd8\xff", "<REDACTED_JPEG>")
    # PNG magic — both forms
    msg = msg.replace(r"\x89PNG", "<REDACTED_PNG>")
    msg = msg.replace("\x89PNG", "<REDACTED_PNG>")
    return msg
