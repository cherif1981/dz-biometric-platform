"""تحميل إعدادات الأمان من YAML مع تجاوز اختياري بمتغيرات البيئة."""
from __future__ import annotations
import os, pathlib
from typing import Any
import yaml


DEFAULT_PATH = "/content/dz-biometric-platform/config/security.yaml"


def _env_override(cfg: dict, path: str, env: str, cast=str) -> None:
    val = os.environ.get(env)
    if val is None:
        return
    parts = path.split('.')
    node = cfg
    for p in parts[:-1]:
        node = node.setdefault(p, {})
    try:
        node[parts[-1]] = cast(val)
    except (ValueError, TypeError):
        pass


class SecurityConfig:
    def __init__(self, path: str = DEFAULT_PATH):
        self.path = path
        self.data: dict[str, Any] = {}
        self.reload()

    def reload(self) -> None:
        p = pathlib.Path(self.path)
        if not p.exists():
            raise FileNotFoundError(f'security config not found: {p}')
        self.data = yaml.safe_load(p.read_text(encoding='utf-8')) or {}
        _env_override(self.data, 'antispoofing.thresholds.reject',
                      'AS_THRESHOLD_REJECT', float)
        _env_override(self.data, 'antispoofing.thresholds.accept',
                      'AS_THRESHOLD_ACCEPT', float)
        _env_override(self.data, 'rate_limiting.per_user.limit',
                      'RL_USER_LIMIT', int)
        _env_override(self.data, 'rate_limiting.per_ip.limit',
                      'RL_IP_LIMIT', int)
        _env_override(self.data, 'rate_limiting.backend',
                      'RL_BACKEND', str)
        _env_override(self.data, 'rate_limiting.redis_url',
                      'REDIS_URL', str)

    @property
    def reject(self) -> float:
        return float(self.data['antispoofing']['thresholds']['reject'])

    @property
    def accept(self) -> float:
        return float(self.data['antispoofing']['thresholds']['accept'])

    def rate_limit(self, scope: str) -> dict:
        return self.data['rate_limiting'][scope]


_cfg: SecurityConfig | None = None


def get_config() -> SecurityConfig:
    global _cfg
    if _cfg is None:
        _cfg = SecurityConfig()
    return _cfg
