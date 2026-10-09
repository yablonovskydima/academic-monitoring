from datetime import datetime, timedelta, timezone

import httpx
import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

import auth_shared.dependencies as dependencies
from auth_shared import Claims, Role, get_verified_claims, require_verified_role
from auth_shared.config import JWT_ALGORITHM, JWT_SECRET_KEY

app = FastAPI()


@app.get("/verified")
def verified(claims: Claims = Depends(get_verified_claims)):
    return claims.model_dump(mode="json")


@app.get("/admin-only")
def admin_only(claims: Claims = Depends(require_verified_role(Role.admin))):
    return {"user_id": claims.user_id}


client = TestClient(app)

AUTHORITY = {"user_id": 3, "role": "admin", "group_ids": [4], "faculty_ids": [5], "session_id": 6}


def token_for(role: str = "curator") -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": "3", "role": role, "type": "access", "exp": now + timedelta(minutes=5)},
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class Authority:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def __call__(self, url, headers=None, timeout=None):
        self.calls.append((url, headers))
        if self.error:
            raise self.error
        return self.response


@pytest.fixture()
def authority(monkeypatch):
    fake = Authority(httpx.Response(200, json=AUTHORITY, request=httpx.Request("GET", "http://auth.test")))
    monkeypatch.setattr(dependencies, "AUTH_SERVICE_URL", "http://auth.test")
    monkeypatch.setattr(dependencies.httpx, "get", fake)
    return fake


def test_claims_come_from_the_authority_not_from_the_token(authority):
    response = client.get("/verified", headers=bearer(token_for("curator")))

    assert response.status_code == 200
    assert response.json() == AUTHORITY


def test_the_callers_token_is_forwarded_to_the_authority(authority):
    token = token_for()

    client.get("/verified", headers=bearer(token))

    url, headers = authority.calls[0]
    assert url == "http://auth.test/auth/introspect"
    assert headers == {"Authorization": f"Bearer {token}"}


def test_authority_saying_401_is_401(authority):
    authority.response = httpx.Response(401, request=httpx.Request("GET", "http://auth.test"))

    assert client.get("/verified", headers=bearer(token_for())).status_code == 401


@pytest.mark.parametrize("code", [429, 500, 503, 404])
def test_any_other_authority_answer_is_503(authority, code):
    authority.response = httpx.Response(code, request=httpx.Request("GET", "http://auth.test"))

    assert client.get("/verified", headers=bearer(token_for())).status_code == 503


def test_unreachable_authority_is_503(authority):
    authority.error = httpx.ConnectError("refused")

    assert client.get("/verified", headers=bearer(token_for())).status_code == 503


def test_garbage_tokens_never_reach_the_authority(authority):
    assert client.get("/verified", headers=bearer("not-a-jwt")).status_code == 401
    assert client.get("/verified").status_code in (401, 403)
    assert authority.calls == []


def test_missing_authority_url_is_a_configuration_error(monkeypatch):
    monkeypatch.setattr(dependencies, "AUTH_SERVICE_URL", None)

    with pytest.raises(RuntimeError, match="AUTH_SERVICE_URL"):
        client.get("/verified", headers=bearer(token_for()))


def test_verified_role_uses_the_authoritative_role(authority):
    assert client.get("/admin-only", headers=bearer(token_for("curator"))).status_code == 200

    authority.response = httpx.Response(
        200, json={**AUTHORITY, "role": "dean"}, request=httpx.Request("GET", "http://auth.test"),
    )
    assert client.get("/admin-only", headers=bearer(token_for("admin"))).status_code == 403
