"""Adapter to unify anti-spoofing service outputs."""
from typing import Any, Dict


def normalize_antispoof_result(raw: Any) -> Dict[str, Any]:
    if raw is None:
        return {"score": 0.0, "is_real": False, "decision": "REJECT"}
    if not isinstance(raw, dict):
        raw = {k: getattr(raw, k) for k in dir(raw) if not k.startswith("_")}
    if "antispoofing_score" in raw:
        return {
            "score": float(raw.get("antispoofing_score") or 0.0),
            "is_real": bool(raw.get("is_live", False)),
            "decision": raw.get("decision", "UNKNOWN"),
        }
    if "score" in raw:
        return {
            "score": float(raw.get("score") or 0.0),
            "is_real": bool(raw.get("is_real", False)),
            "decision": raw.get("decision", "UNKNOWN"),
        }
    return {"score": 0.0, "is_real": False, "decision": "REJECT"}
