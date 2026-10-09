import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from auth_shared import InvalidTokenError, decode_and_verify
from fastapi import Request

from auth_service.config import (
    RATE_LIMIT_AUTHENTICATED_MAX,
    RATE_LIMIT_IP_MAX,
    RATE_LIMIT_UNAUTHENTICATED_MAX,
    RATE_LIMIT_WINDOW_SECONDS,
)

EXEMPT_PATHS = frozenset({"/health"})
IP_BUCKET_EXEMPT_PATHS = frozenset({"/auth/introspect"})


class RateLimitExceeded(Exception):
    def __init__(self, retry_after: float):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded, retry after {retry_after:.1f}s")


@dataclass
class _Bucket:
    window_start: float
    count: int


class InMemoryRateLimiter:
    def __init__(self, window_seconds: float, clock: Callable[[], float] = time.monotonic):
        self.window_seconds = window_seconds
        self._clock = clock
        self._buckets: dict[str, _Bucket] = {}
        self._last_sweep = clock()
        self._lock = threading.Lock()

    def hit(self, key: str, limit: int) -> None:
        now = self._clock()
        with self._lock:
            self._sweep_expired(now)

            bucket = self._buckets.get(key)
            if bucket is None or now - bucket.window_start >= self.window_seconds:
                self._buckets[key] = _Bucket(window_start=now, count=1)
                return

            if bucket.count >= limit:
                raise RateLimitExceeded(retry_after=max(self.window_seconds - (now - bucket.window_start), 0.0))

            bucket.count += 1

    def bucket_count(self) -> int:
        with self._lock:
            return len(self._buckets)

    def reset(self) -> None:
        with self._lock:
            self._buckets.clear()
            self._last_sweep = self._clock()

    def _sweep_expired(self, now: float) -> None:
        if now - self._last_sweep < self.window_seconds:
            return

        expired = [key for key, bucket in self._buckets.items() if now - bucket.window_start >= self.window_seconds]
        for key in expired:
            del self._buckets[key]
        self._last_sweep = now


_limiter = InMemoryRateLimiter(window_seconds=RATE_LIMIT_WINDOW_SECONDS)


def reset_rate_limiter() -> None:
    _limiter.reset()


def _resolve_identity(request: Request, client_ip: str) -> tuple[str, int]:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            claims = decode_and_verify(auth_header.removeprefix("Bearer "))
            return f"user:{claims.user_id}", RATE_LIMIT_AUTHENTICATED_MAX
        except InvalidTokenError:
            pass

    return f"anon:{client_ip}", RATE_LIMIT_UNAUTHENTICATED_MAX


def rate_limit(request: Request) -> None:
    if request.url.path in EXEMPT_PATHS:
        return

    client_ip = request.client.host if request.client else "unknown"

    if request.url.path not in IP_BUCKET_EXEMPT_PATHS:
        _limiter.hit(f"ip:{client_ip}", RATE_LIMIT_IP_MAX)

    identity_key, identity_limit = _resolve_identity(request, client_ip)
    _limiter.hit(identity_key, identity_limit)
