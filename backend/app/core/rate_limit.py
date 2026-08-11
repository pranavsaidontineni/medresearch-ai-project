import time
from collections import defaultdict, deque
from threading import Lock
from fastapi import Request
from fastapi.responses import JSONResponse


class InMemoryRateLimiter:
    """Small-process development limiter; use Redis for multi-instance production."""

    def __init__(self, limit: int = 60, window_seconds: int = 60):
        self.limit = limit
        self.window_seconds = window_seconds
        self._events = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= self.limit:
                return False
            events.append(now)
            return True


request_limiter = InMemoryRateLimiter()


async def rate_limit_middleware(request: Request, call_next):
    # Health checks and docs are intentionally not throttled.
    if request.url.path in {"/health", "/docs", "/openapi.json", "/redoc"}:
        return await call_next(request)
    client = request.client.host if request.client else "unknown"
    if not request_limiter.allow(f"{client}:{request.url.path}"):
        return JSONResponse(status_code=429, content={"detail": "Too many requests. Please try again shortly."})
    return await call_next(request)
