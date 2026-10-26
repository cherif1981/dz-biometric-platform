"""
Single Source of Truth for decision thresholds.

Rules:
- config/thresholds.yaml is the ONLY source of values (checked-in).
- Environment variables are OVERRIDES only (must already exist in YAML).
- Missing file, missing key, non-numeric value, or value outside [0,1]
  → raises immediately (fail-fast, no silent defaults).
"""
from functools import lru_cache
from pathlib import Path
from typing import Dict
import os
import yaml

_DEFAULT_PATH = Path("config/thresholds.yaml")
_REQUIRED = (
    "face_similarity",
    "liveness",
    "antispoofing",
    "antispoofing_reject",
    "antispoofing_accept",
    "ocr_confidence",
)
_ENV_OVERRIDES = {
    "face_similarity": "FACE_SIMILARITY_THRESHOLD",
    "liveness": "LIVENESS_THRESHOLD",
    "antispoofing": "ANTISPOOFING_THRESHOLD",
    "antispoofing_reject": "AS_REJECT_THRESHOLD",
    "antispoofing_accept": "AS_ACCEPT_THRESHOLD",
    "ocr_confidence": "OCR_CONFIDENCE_THRESHOLD",
}


class Thresholds:
    def __init__(self, data: Dict):
        missing = [k for k in _REQUIRED if k not in data]
        if missing:
            raise ValueError(f"thresholds.yaml: missing required keys {missing}")

        for k in _REQUIRED:
            v = data[k]
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                raise ValueError(f"threshold '{k}'={v!r} is not numeric")
            if not 0.0 <= float(v) <= 1.0:
                raise ValueError(f"threshold '{k}'={v} outside [0,1]")

        self.face_similarity = float(data["face_similarity"])
        self.liveness = float(data["liveness"])
        self.antispoofing = float(data["antispoofing"])
        self.antispoofing_reject = float(data["antispoofing_reject"])
        self.antispoofing_accept = float(data["antispoofing_accept"])
        self.ocr_confidence = float(data["ocr_confidence"])

        # Cross-validation: three-way policy must satisfy reject < accept
        if not (self.antispoofing_reject < self.antispoofing_accept):
            raise ValueError(
                f"antispoofing thresholds invalid: must satisfy "
                f"reject < accept, got reject={self.antispoofing_reject}, "
                f"accept={self.antispoofing_accept}"
            )

    def as_dict(self) -> Dict[str, float]:
        return {k: getattr(self, k) for k in _REQUIRED}

    def __repr__(self) -> str:
        return f"Thresholds({self.as_dict()})"


@lru_cache(maxsize=1)
def get_thresholds() -> Thresholds:
    """Load and validate thresholds. Called by every engine — same values for all."""
    path = Path(os.getenv("THRESHOLDS_PATH", str(_DEFAULT_PATH)))
    if not path.exists():
        raise FileNotFoundError(
            f"Thresholds file not found: {path}. "
            "Refusing to start — absence of config is NOT success."
        )

    with path.open(encoding='utf-8') as f:
        data = yaml.safe_load(f) or {}

    for key, env_name in _ENV_OVERRIDES.items():
        env_val = os.getenv(env_name)
        if env_val is None:
            continue
        if key not in data:
            raise ValueError(
                f"Env override {env_name} set but '{key}' absent from YAML. "
                "YAML is the source of truth; add the key there first."
            )
        try:
            data[key] = float(env_val)
        except ValueError:
            raise ValueError(f"Env override {env_name}={env_val!r} is not numeric")

    return Thresholds(data)


def reset_cache() -> None:
    """For tests: force re-read of YAML."""
    get_thresholds.cache_clear()
