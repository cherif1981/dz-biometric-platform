"""
محدّد معدل الطلبات - Sliding Window.
في Colab: تخزين في الذاكرة. في الإنتاج: استبدل Backend بـ Redis.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Literal


@dataclass
class RateLimitDecision:
    allowed: bool
    remaining: int
    retry_after: float  # ثوانٍ حتى يُسمح بالمحاولة التالية
    reason: Literal["ok", "limit_exceeded", "blocked"]


class InMemoryBackend:
    """Backend بسيط، thread-safe، مناسب لبيئة واحدة أو للاختبار."""

    def __init__(self):
        self._buckets: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str, window: float, limit: int) -> RateLimitDecision:
        now = time.monotonic()
        with self._lock:
            q = self._buckets[key]
            # أزل الطلبات الأقدم من النافذة
            cutoff = now - window
            while q and q[0] < cutoff:
                q.popleft()
            if len(q) >= limit:
                retry_after = max(0.0, window - (now - q[0]))
                return RateLimitDecision(False, 0, retry_after, "limit_exceeded")
            q.append(now)
            return RateLimitDecision(True, limit - len(q), 0.0, "ok")

    def reset(self, key: str) -> None:
        with self._lock:
            self._buckets.pop(key, None)


class RateLimiter:
    """
    سياستان مستقلتان تُطبَّقان معًا على كل طلب:
    - per_user: عدد الطلبات لكل مستخدم في النافذة
    - per_ip:   عدد الطلبات لكل IP في النافذة
    القرار = الأكثر تقييدًا.
    """

    def __init__(
        self,
        *,
        backend: InMemoryBackend | None = None,
        user_window: float = 60.0,
        user_limit: int = 10,
        ip_window: float = 60.0,
        ip_limit: int = 30,
    ):
        self.backend = backend or InMemoryBackend()
        self.user_window = user_window
        self.user_limit = user_limit
        self.ip_window = ip_window
        self.ip_limit = ip_limit

    def check(
        self,
        *,
        user_id: str | None,
        ip: str | None,
    ) -> RateLimitDecision:
        """
        يعيد أول قرار رفض. إن مرّ الجميع، يعيد قرار السماح بـ remaining الأدنى.
        """
        decisions: list[RateLimitDecision] = []

        if user_id:
            decisions.append(self.backend.hit(f"u:{user_id}", self.user_window, self.user_limit))
        if ip:
            decisions.append(self.backend.hit(f"ip:{ip}", self.ip_window, self.ip_limit))

        if not decisions:
            return RateLimitDecision(True, 0, 0.0, "ok")

        # 📊 Prometheus
        try:
            from src.services import metrics as _m

            blocked = any(not d.allowed for d in decisions)
            _m.record_rate_limit("per_user" if user_id else "per_ip", blocked)
        except Exception:
            pass
        # الأكثر تقييدًا
        for d in decisions:
            if not d.allowed:
                return d
        return min(decisions, key=lambda d: d.remaining)


# نسخة عامة (singleton) يستخدمها التطبيق
_default_limiter: RateLimiter | None = None


def get_default_limiter() -> RateLimiter:
    global _default_limiter
    if _default_limiter is None:
        _default_limiter = RateLimiter()
    return _default_limiter


# ═══════════════════════════════════════════════════════════════════
# Redis Backend — للإنتاج متعدد الخوادم (atomic, distributed)
# ═══════════════════════════════════════════════════════════════════
class RedisBackend:
    """
    Sliding window atomic باستخدام Redis sorted set.
    آمن عبر عدة خوادم. يستخدم Lua script لضمان الذرّية.
    """

    LUA_SCRIPT = """
    local key = KEYS[1]
    local now = tonumber(ARGV[1])
    local window = tonumber(ARGV[2])
    local limit = tonumber(ARGV[3])

    redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
    local count = redis.call('ZCARD', key)
    if count < limit then
        redis.call('ZADD', key, now, now .. '-' .. math.random())
        redis.call('EXPIRE', key, math.ceil(window) + 1)
        return {1, limit - count - 1, 0}
    end
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    local retry = 0
    if oldest and oldest[2] then
        retry = tonumber(oldest[2]) + window - now
    end
    return {0, 0, retry}
    """

    def __init__(self, client):
        """client: redis.Redis instance (decode_responses=False)."""
        self.r = client
        self._script = self.r.register_script(self.LUA_SCRIPT)

    def hit(self, key: str, window: float, limit: int) -> "RateLimitDecision":
        import time

        now = time.time()
        allowed, remaining, retry = self._script(
            keys=[f"rl:{key}"],
            args=[now, window, limit],
        )
        return RateLimitDecision(
            allowed=bool(allowed),
            remaining=int(remaining),
            retry_after=float(retry),
            reason="ok" if allowed else "limit_exceeded",
        )

    def reset(self, key: str) -> None:
        self.r.delete(f"rl:{key}")


def build_backend(kind: str = "memory", redis_url: str | None = None):
    """
    ينشئ backend مناسب حسب الإعدادات.
    kind: "memory" | "redis"
    """
    if kind == "redis":
        try:
            import redis  # noqa
        except ImportError:
            raise RuntimeError("redis-py غير مثبت: pip install redis")
        import redis as _redis

        if not redis_url:
            raise ValueError("redis_url مطلوب لـ redis backend")
        client = _redis.from_url(redis_url, decode_responses=False)
        # اختبار الاتصال
        client.ping()
        return RedisBackend(client)
    return InMemoryBackend()
