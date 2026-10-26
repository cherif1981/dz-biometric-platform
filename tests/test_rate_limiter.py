
import time
from src.services.rate_limiter import RateLimiter


def test_per_user_limit():
    lim = RateLimiter(user_window=10, user_limit=2, ip_window=10, ip_limit=100)
    assert lim.check(user_id="u1", ip="1.1.1.1").allowed
    assert lim.check(user_id="u1", ip="1.1.1.1").allowed
    d = lim.check(user_id="u1", ip="1.1.1.1")
    assert not d.allowed and d.retry_after > 0


def test_per_ip_limit_independent_of_user():
    lim = RateLimiter(user_window=10, user_limit=100, ip_window=10, ip_limit=2)
    assert lim.check(user_id="a", ip="9.9.9.9").allowed
    assert lim.check(user_id="b", ip="9.9.9.9").allowed
    d = lim.check(user_id="c", ip="9.9.9.9")
    assert not d.allowed


def test_window_slides():
    lim = RateLimiter(user_window=0.3, user_limit=1, ip_window=0.3, ip_limit=100)
    assert lim.check(user_id="u", ip="1.1.1.1").allowed
    assert not lim.check(user_id="u", ip="1.1.1.1").allowed
    time.sleep(0.35)
    assert lim.check(user_id="u", ip="1.1.1.1").allowed
