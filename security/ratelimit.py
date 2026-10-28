"""Distributed rate limiter using Redis.

Design:
- Try EVAL (Lua) directly — no SCRIPT LOAD, which fakeredis doesn't support.
- On any failure, fall back to a pipeline-based INCR+EXPIRE (good enough
  for dev/testing; production Redis Cluster should use the Lua path).
"""
from typing import Optional


class RateLimitExceeded(Exception):
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded; retry after {retry_after}s")


_LUA = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
local ttl = redis.call('TTL', KEYS[1])
return {current, ttl}
"""


class RateLimiter:
    def __init__(self, redis_client, limit: int, window_seconds: int,
                 force_fallback: bool = False):
        self.redis = redis_client
        self.limit = limit
        self.window = window_seconds
        self._use_lua = not force_fallback
        self._last_path = "lua" if self._use_lua else "fallback"

    def _check_lua(self, key):
        """Direct EVAL — works on real Redis, may fail on fakeredis."""
        return self.redis.eval(_LUA, 1, key, self.window)

    def _check_fallback(self, key):
        """Non-atomic INCR + EXPIRE — acceptable for dev/test only."""
        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.ttl(key)
        current, ttl = pipe.execute()
        current = int(current)
        if current == 1 or int(ttl) < 0:
            self.redis.expire(key, self.window)
            ttl = self.window
        return [current, ttl]

    def check(self, key: str) -> dict:
        """Raise RateLimitExceeded if limit exceeded; else return state."""
        try:
            if self._use_lua:
                current, ttl = self._check_lua(key)
            else:
                current, ttl = self._check_fallback(key)
        except Exception:
            # Permanent switch to fallback for this instance
            self._use_lua = False
            self._last_path = "fallback"
            current, ttl = self._check_fallback(key)

        current, ttl = int(current), int(ttl)
        remaining = max(0, self.limit - current)
        if current > self.limit:
            raise RateLimitExceeded(retry_after=ttl if ttl > 0 else self.window)
        return {"current": current, "remaining": remaining, "ttl": ttl}

    @property
    def path(self) -> str:
        """Which code path is active: 'lua' or 'fallback'."""
        return self._last_path
