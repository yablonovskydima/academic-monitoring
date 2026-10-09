import pytest

from auth_service.clients.import_service_client import ImportServiceClient
from auth_service.models.user import UserRoleEnum
from auth_service.services.password_reset_token_service import PasswordResetTokenService
from auth_service.utils import events
from helpers import PASSWORD, auth_headers, login, make_user


@pytest.fixture(autouse=True)
def fake_import_service(monkeypatch):
    monkeypatch.setattr(ImportServiceClient, "get_group", lambda self, group_id: {"id": group_id})
    monkeypatch.setattr(ImportServiceClient, "get_faculty", lambda self, faculty_id: {"id": faculty_id})


@pytest.fixture()
def published(monkeypatch):
    captured = []
    monkeypatch.setattr(events, "publish_event", lambda event, payload: captured.append((event.value, payload)))
    return captured


@pytest.fixture()
def admin_headers(client, db_session):
    make_user(db_session, UserRoleEnum.admin, "eventful@example.com")
    return auth_headers(login(client, "eventful@example.com")["access_token"])


def _session_id(client, access_token):
    return client.get("/auth/introspect", headers=auth_headers(access_token)).json()["session_id"]


def test_logging_in_publishes_nothing(client, db_session, published):
    make_user(db_session, UserRoleEnum.curator, "quiet@example.com")

    login(client, "quiet@example.com")

    assert published == []


def test_deactivation_is_published_but_activation_is_not(client, db_session, admin_headers, published):
    target = make_user(db_session, UserRoleEnum.curator, "toggled@example.com")

    client.post(f"/users/{target.id}/deactivate", headers=admin_headers)
    client.post(f"/users/{target.id}/activate", headers=admin_headers)

    assert published == [("auth.user.deactivated", {"user_id": target.id})]


def test_rejected_user_changes_publish_nothing(client, db_session, admin_headers, published):
    admin = make_user(db_session, UserRoleEnum.admin, "bystander@example.com")
    me = client.get("/auth/me", headers=admin_headers).json()

    client.post(f"/users/{me['id']}/deactivate", headers=admin_headers)
    client.post(f"/users/{me['id']}/role", headers=admin_headers, json={"role": "curator"})
    client.delete(f"/users/{me['id']}", headers=admin_headers)
    client.post("/users/999999/deactivate", headers=admin_headers)
    client.delete("/users/999999", headers=admin_headers)
    client.post(f"/users/{admin.id}/role", headers=admin_headers, json={"role": "admin"})

    assert published == []


def test_deleting_a_user_is_published(client, db_session, admin_headers, published):
    target = make_user(db_session, UserRoleEnum.curator, "removed@example.com")

    client.delete(f"/users/{target.id}", headers=admin_headers)

    assert published == [("auth.user.deleted", {"user_id": target.id})]


def test_role_change_publishes_the_change_and_a_full_session_revocation(client, db_session, admin_headers, published):
    target = make_user(db_session, UserRoleEnum.curator, "reassigned@example.com")

    client.post(f"/users/{target.id}/role", headers=admin_headers, json={"role": "dean"})

    assert published == [
        ("auth.user.role_changed", {"user_id": target.id, "old_role": "curator", "new_role": "dean"}),
        ("auth.session.revoked", {"user_id": target.id, "session_id": None}),
    ]


def test_curator_assignments_publish_scope_changes(client, db_session, published):
    curator = make_user(db_session, UserRoleEnum.curator, "scoped@example.com")
    headers = auth_headers(login(client, "scoped@example.com")["access_token"])

    created = client.post("/curator-assignments/", headers=headers, json={"group_id": 3}).json()
    client.post("/curator-assignments/", headers=headers, json={"group_id": 3})
    client.delete(f"/curator-assignments/{created['id']}", headers=headers)

    assert published == [
        ("auth.user.scopes_changed", {"user_id": curator.id}),
        ("auth.user.scopes_changed", {"user_id": curator.id}),
    ]


def test_dean_assignments_publish_scope_changes_for_the_dean(client, db_session, admin_headers, published):
    dean = make_user(db_session, UserRoleEnum.dean, "scopeddean@example.com")

    created = client.post(
        "/dean-assignments/", headers=admin_headers, json={"dean_user_id": dean.id, "faculty_id": 2},
    ).json()
    client.delete(f"/dean-assignments/{created['id']}", headers=admin_headers)

    assert published == [
        ("auth.user.scopes_changed", {"user_id": dean.id}),
        ("auth.user.scopes_changed", {"user_id": dean.id}),
    ]


def test_logout_publishes_the_revoked_session(client, db_session, published):
    user = make_user(db_session, UserRoleEnum.curator, "leaving@example.com")
    tokens = login(client, "leaving@example.com")
    session_id = _session_id(client, tokens["access_token"])

    client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]})

    assert published == [("auth.session.revoked", {"user_id": user.id, "session_id": session_id})]


def test_logout_with_an_unknown_token_publishes_nothing(client, published):
    client.post("/auth/logout", json={"refresh_token": "not-a-real-token"})

    assert published == []


def test_refresh_publishes_the_replaced_session(client, db_session, published):
    user = make_user(db_session, UserRoleEnum.curator, "rotating@example.com")
    tokens = login(client, "rotating@example.com")
    old_session = _session_id(client, tokens["access_token"])

    client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

    assert published == [("auth.session.revoked", {"user_id": user.id, "session_id": old_session})]


def test_revoke_all_and_password_changes_publish_a_full_revocation(client, db_session, published):
    user = make_user(db_session, UserRoleEnum.curator, "everywhere@example.com")
    headers = auth_headers(login(client, "everywhere@example.com")["access_token"])

    client.post("/auth/revoke-all", headers=headers)
    headers = auth_headers(login(client, "everywhere@example.com")["access_token"])
    client.post("/auth/change-password", headers=headers, json={
        "current_password": PASSWORD,
        "new_password": "NewStr0ng!Pass",
        "confirm_new_password": "NewStr0ng!Pass",
    })
    token = PasswordResetTokenService(db_session).issue(user.id).raw_token
    client.post("/auth/reset-password", json={
        "token": token,
        "new_password": "AnotherStr0ng!Pass",
        "confirm_new_password": "AnotherStr0ng!Pass",
    })

    assert published == [("auth.session.revoked", {"user_id": user.id, "session_id": None})] * 3


def test_failed_password_change_publishes_nothing(client, db_session, published):
    make_user(db_session, UserRoleEnum.curator, "wrongpass@example.com")
    headers = auth_headers(login(client, "wrongpass@example.com")["access_token"])

    client.post("/auth/change-password", headers=headers, json={
        "current_password": "Wrong#Pass1",
        "new_password": "NewStr0ng!Pass",
        "confirm_new_password": "NewStr0ng!Pass",
    })

    assert published == []
