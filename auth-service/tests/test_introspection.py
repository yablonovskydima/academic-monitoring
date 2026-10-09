import pytest
from auth_shared import Claims, Role, get_claims, get_verified_claims, require_verified_role
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

import auth_service.utils.rate_limit as rate_limit_module
from auth_service.clients.import_service_client import ImportServiceClient
from auth_service.models.user import UserRoleEnum
from helpers import auth_headers, login, make_user

AUTH_URL = "http://auth.test"

consumer = FastAPI()


@consumer.get("/stateless")
def stateless(claims: Claims = Depends(get_claims)):
    return claims.model_dump(mode="json")


@consumer.get("/verified")
def verified(claims: Claims = Depends(get_verified_claims)):
    return claims.model_dump(mode="json")


@consumer.get("/verified-admin")
def verified_admin(claims: Claims = Depends(require_verified_role(Role.admin))):
    return {"user_id": claims.user_id}


@pytest.fixture(autouse=True)
def fake_import_service(monkeypatch):
    monkeypatch.setattr(ImportServiceClient, "get_group", lambda self, group_id: {"id": group_id})


@pytest.fixture()
def bff(client, monkeypatch):
    import auth_shared.dependencies as shared

    def forward(url, headers=None, timeout=None):
        return client.get(url.removeprefix(AUTH_URL), headers=headers)

    monkeypatch.setattr(shared, "AUTH_SERVICE_URL", AUTH_URL)
    monkeypatch.setattr(shared.httpx, "get", forward)
    return TestClient(consumer)


def _admin(client, db_session, email="authority@example.com"):
    user = make_user(db_session, UserRoleEnum.admin, email)
    return user, login(client, email)["access_token"]


def test_introspect_returns_current_claims(client, db_session):
    user = make_user(db_session, UserRoleEnum.curator, "introspected@example.com")
    token = login(client, "introspected@example.com")["access_token"]
    client.post("/curator-assignments/", headers=auth_headers(token), json={"group_id": 11})

    response = client.get("/auth/introspect", headers=auth_headers(token))

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == user.id
    assert body["role"] == "curator"
    assert body["group_ids"] == [11]
    assert body["faculty_ids"] == []
    assert body["session_id"] is not None


def test_introspect_rejects_missing_invalid_and_revoked_tokens(client, db_session):
    make_user(db_session, UserRoleEnum.curator, "revoked@example.com")
    tokens = login(client, "revoked@example.com")

    assert client.get("/auth/introspect").status_code in (401, 403)
    assert client.get("/auth/introspect", headers=auth_headers("garbage")).status_code == 401

    client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert client.get("/auth/introspect", headers=auth_headers(tokens["access_token"])).status_code == 401


def test_introspect_is_not_capped_by_the_ip_bucket(client, db_session, monkeypatch):
    monkeypatch.setattr(rate_limit_module, "RATE_LIMIT_IP_MAX", 3)
    make_user(db_session, UserRoleEnum.curator, "gateway@example.com")
    token = login(client, "gateway@example.com")["access_token"]

    statuses = [client.get("/auth/introspect", headers=auth_headers(token)).status_code for _ in range(5)]

    assert statuses == [200] * 5


def test_verified_claims_see_new_assignments_but_the_token_does_not(client, db_session, bff):
    make_user(db_session, UserRoleEnum.curator, "growing@example.com")
    token = login(client, "growing@example.com")["access_token"]
    client.post("/curator-assignments/", headers=auth_headers(token), json={"group_id": 21})

    stale = bff.get("/stateless", headers=auth_headers(token)).json()
    fresh = bff.get("/verified", headers=auth_headers(token)).json()

    assert stale["group_ids"] == []
    assert fresh["group_ids"] == [21]


def test_verified_claims_reject_a_deactivated_admin_that_the_token_alone_accepts(client, db_session, bff):
    victim, victim_token = _admin(client, db_session, "doomed@example.com")
    _, other_token = _admin(client, db_session, "survivor@example.com")
    client.post(f"/users/{victim.id}/deactivate", headers=auth_headers(other_token))

    assert bff.get("/stateless", headers=auth_headers(victim_token)).status_code == 200
    assert bff.get("/verified", headers=auth_headers(victim_token)).status_code == 401
    assert bff.get("/verified-admin", headers=auth_headers(victim_token)).status_code == 401


def test_verified_claims_reject_a_revoked_session(client, db_session, bff):
    make_user(db_session, UserRoleEnum.curator, "loggedout@example.com")
    tokens = login(client, "loggedout@example.com")
    assert bff.get("/verified", headers=auth_headers(tokens["access_token"])).status_code == 200

    client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

    assert bff.get("/verified", headers=auth_headers(tokens["access_token"])).status_code == 401


def test_verified_role_follows_the_current_role_not_the_one_in_the_token(client, db_session, bff):
    _, admin_token = _admin(client, db_session, "promoter@example.com")
    user = make_user(db_session, UserRoleEnum.curator, "promoted@example.com")
    old_token = login(client, "promoted@example.com")["access_token"]
    assert bff.get("/verified-admin", headers=auth_headers(old_token)).status_code == 403

    client.post(f"/users/{user.id}/role", headers=auth_headers(admin_token), json={"role": "admin"})
    new_token = login(client, "promoted@example.com")["access_token"]

    assert bff.get("/verified-admin", headers=auth_headers(new_token)).status_code == 200
    assert bff.get("/verified-admin", headers=auth_headers(old_token)).status_code == 401
