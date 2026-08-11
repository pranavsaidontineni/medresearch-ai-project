from app.core.rate_limit import InMemoryRateLimiter


def test_rate_limiter_allows_limit_then_blocks():
    limiter = InMemoryRateLimiter(limit=2, window_seconds=60)
    assert limiter.allow("client") is True
    assert limiter.allow("client") is True
    assert limiter.allow("client") is False


def test_rate_limiter_is_per_key():
    limiter = InMemoryRateLimiter(limit=1, window_seconds=60)
    assert limiter.allow("a") is True
    assert limiter.allow("b") is True
