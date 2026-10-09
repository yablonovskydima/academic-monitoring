import pytest

import auth_service.utils.rate_limit as rate_limit_module
from auth_service.config import RATE_LIMIT_UNAUTHENTICATED_MAX
from auth_service.models.user import UserRoleEnum
from auth_service.utils.rate_limit import InMemoryRateLimiter, RateLimitExceeded
from helpers import auth_headers, login, make_user


class _FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


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


def test_expired_buckets_are_removed_from_memory():
    clock = _FakeClock()
    limiter = InMemoryRateLimiter(window_seconds=10, clock=clock)
    for i in range(50):
        limiter.hit(f"key-{i}", 5)
    assert limiter.bucket_count() == 50

    clock.advance(11)
    limiter.hit("fresh", 5)

    assert limiter.bucket_count() == 1


def test_active_buckets_survive_a_sweep():
    clock = _FakeClock()
    limiter = InMemoryRateLimiter(window_seconds=10, clock=clock)
    limiter.hit("old", 1)
    clock.advance(6)
    limiter.hit("recent", 1)
    clock.advance(5)

    limiter.hit("trigger", 5)

    assert limiter.bucket_count() == 2
    with pytest.raises(RateLimitExceeded):
        limiter.hit("recent", 1)


@pytest.mark.parametrize("method,path", [
    ("get", "/users/"),
    ("get", "/users/1"),
    ("get", "/audit-log/"),
    ("get", "/curator-assignments/me"),
    ("get", "/dean-assignments/1"),
    ("get", "/auth/me"),
    ("post", "/auth/login"),
])
def test_every_endpoint_is_rate_limited(client, method, path):
    statuses = [
        getattr(client, method)(path, **({"json": {"login": "nobody", "password": "x"}} if method == "post" else {})).status_code
        for _ in range(RATE_LIMIT_UNAUTHENTICATED_MAX + 1)
    ]

    assert statuses[-1] == 429
    assert 429 not in statuses[:-1]


def test_health_endpoint_is_exempt(client):
    statuses = {client.get("/health").status_code for _ in range(RATE_LIMIT_UNAUTHENTICATED_MAX * 3)}

    assert statuses == {200}


def test_authenticated_users_are_also_limited_per_ip(client, db_session, monkeypatch):
    monkeypatch.setattr(rate_limit_module, "RATE_LIMIT_IP_MAX", 5)
    make_user(db_session, UserRoleEnum.curator, "natuser.a@example.com")
    make_user(db_session, UserRoleEnum.curator, "natuser.b@example.com")
    a = auth_headers(login(client, "natuser.a@example.com")["access_token"])
    b = auth_headers(login(client, "natuser.b@example.com")["access_token"])

    a_statuses = [client.get("/auth/me", headers=a).status_code for _ in range(4)]
    b_status = client.get("/auth/me", headers=b).status_code

    assert a_statuses == [200, 200, 200, 429]
    assert b_status == 429


def test_users_have_independent_buckets(client, db_session, monkeypatch):
    monkeypatch.setattr(rate_limit_module, "RATE_LIMIT_AUTHENTICATED_MAX", 3)
    make_user(db_session, UserRoleEnum.curator, "indep.a@example.com")
    make_user(db_session, UserRoleEnum.curator, "indep.b@example.com")
    a = auth_headers(login(client, "indep.a@example.com")["access_token"])
    b = auth_headers(login(client, "indep.b@example.com")["access_token"])

    a_statuses = [client.get("/auth/me", headers=a).status_code for _ in range(4)]
    b_statuses = [client.get("/auth/me", headers=b).status_code for _ in range(3)]

    assert a_statuses == [200, 200, 200, 429]
    assert b_statuses == [200, 200, 200]


def test_anonymous_and_authenticated_traffic_use_separate_buckets(client, db_session):
    make_user(db_session, UserRoleEnum.curator, "mixed@example.com")
    headers = auth_headers(login(client, "mixed@example.com")["access_token"])

    for _ in range(RATE_LIMIT_UNAUTHENTICATED_MAX):
        client.get("/auth/me")

    assert client.get("/auth/me").status_code == 429
    assert client.get("/auth/me", headers=headers).status_code == 200
