from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

_THIS = Path(__file__).resolve()


def _find_project_root(start: Path) -> Path:
    for p in [start, *start.parents]:
        if (p / "pyproject.toml").exists() or (p / ".git").exists():
            return p
    return start.parent


PROJECT_ROOT = _find_project_root(_THIS.parent)


@dataclass(frozen=True)
class Settings:
    project_root: Path
    config_dir: Path
    security_yaml: Path
    pad_model_path: Path
    pad_attest_dir: Path
    pad_attest_key_b64: Optional[str]
    database_url: str
    debug: bool


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    root = PROJECT_ROOT
    config_dir = Path(os.environ.get("APP_CONFIG_DIR", str(root / "config"))).resolve()
    return Settings(
        project_root=root,
        config_dir=config_dir,
        security_yaml=Path(
            os.environ.get("SECURITY_CONFIG_PATH", str(config_dir / "security.yaml"))
        ).resolve(),
        pad_model_path=Path(
            os.environ.get(
                "PAD_MODEL_PATH", str(root / "anti_spoof/models/MiniFASNetV2.onnx")
            )
        ).resolve(),
        pad_attest_dir=Path(
            os.environ.get("PAD_ATTEST_DIR", str(root / "anti_spoof/attestation"))
        ).resolve(),
        pad_attest_key_b64=os.environ.get("PAD_ATTEST_KEY_B64"),
        database_url=os.environ.get("DATABASE_URL", f"sqlite:///{root / 'app.db'}"),
        debug=os.environ.get("DEBUG", "false").lower() in ("1", "true", "yes"),
    )


def reload_settings() -> None:
    get_settings.cache_clear()
