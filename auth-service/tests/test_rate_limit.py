import pytest

from auth_service.config import RATE_LIMIT_UNAUTHENTICATED_MAX
from auth_service.models.user import UserRoleEnum
from auth_service.rate_limit import InMemoryRateLimiter, RateLimitExceeded
from helpers import auth_headers, login, make_user


class _FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_limiter_allows_requests_up_to_the_limit():
    limiter = InMemoryRateLimiter(window_seconds=10, clock=_FakeClock())

    for _ in range(5):
        limiter.hit("key", 5)


def test_limiter_blocks_once_the_limit_is_exceeded():
    limiter = InMemoryRateLimiter(window_seconds=10, clock=_FakeClock())

    for _ in range(5):
        limiter.hit("key", 5)

    with pytest.raises(RateLimitExceeded):
        limiter.hit("key", 5)


def test_limiter_reports_a_sane_retry_after():
    clock = _FakeClock()
    limiter = InMemoryRateLimiter(window_seconds=10, clock=clock)

    for _ in range(3):
        limiter.hit("key", 3)
    clock.advance(4)

    with pytest.raises(RateLimitExceeded) as excinfo:
        limiter.hit("key", 3)

    assert 5.5 <= excinfo.value.retry_after <= 6.5


def test_limiter_resets_once_the_window_passes():
    clock = _FakeClock()
    limiter = InMemoryRateLimiter(window_seconds=10, clock=clock)

    for _ in range(3):
        limiter.hit("key", 3)
    clock.advance(10)

    limiter.hit("key", 3)


def test_limiter_tracks_keys_independently():
    limiter = InMemoryRateLimiter(window_seconds=10, clock=_FakeClock())

    for _ in range(3):
        limiter.hit("a", 3)

    limiter.hit("b", 3)


def test_reset_clears_all_buckets():
    limiter = InMemoryRateLimiter(window_seconds=10, clock=_FakeClock())

    for _ in range(3):
        limiter.hit("key", 3)
    limiter.reset()

    limiter.hit("key", 3)


def test_unauthenticated_requests_are_rate_limited(client):
    for _ in range(RATE_LIMIT_UNAUTHENTICATED_MAX):
        response = client.post("/auth/forgot-password", json={"login": "nobody"})
        assert response.status_code == 202

    blocked = client.post("/auth/forgot-password", json={"login": "nobody"})

    assert blocked.status_code == 429
    assert blocked.json() == {"detail": "Too many requests. Please try again later."}
    assert "Retry-After" in blocked.headers


def test_authenticated_requests_use_a_separate_higher_limit(client, db_session):
    make_user(db_session, UserRoleEnum.curator, "ratelimit@example.com")
    tokens = login(client, "ratelimit@example.com")

    for _ in range(RATE_LIMIT_UNAUTHENTICATED_MAX + 1):
        response = client.get("/auth/me", headers=auth_headers(tokens["access_token"]))
        assert response.status_code == 200
