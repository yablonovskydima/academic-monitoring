import pytest
from sqlalchemy.exc import IntegrityError

from auth_service.clients.import_service_client import ImportServiceClient
from auth_service.models.audit_log import AuditLog
from auth_service.models.curator_group_assignment import CuratorGroupAssignment
from auth_service.models.password_reset_token import PasswordResetToken
from auth_service.models.refresh_token import RefreshToken
from auth_service.models.user import UserRoleEnum
from auth_service.services.password_reset_token_service import PasswordResetTokenService
from helpers import PASSWORD, auth_headers, login, make_user


@pytest.fixture(autouse=True)
def fake_import_service(monkeypatch):
    monkeypatch.setattr(ImportServiceClient, "get_group", lambda self, group_id: {"id": group_id})
    monkeypatch.setattr(ImportServiceClient, "get_faculty", lambda self, faculty_id: {"id": faculty_id})


@pytest.fixture()
def admin_headers(client, db_session):
    make_user(db_session, UserRoleEnum.admin, "deleter@example.com")
    return auth_headers(login(client, "deleter@example.com")["access_token"])


def test_foreign_keys_are_enforced_in_tests(db_session):
    db_session.add(CuratorGroupAssignment(user_id=999999, group_id=1))

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_admin_deletes_a_user_with_all_their_data(client, db_session, admin_headers):
    victim = make_user(db_session, UserRoleEnum.curator, "victim@example.com")
    victim_tokens = login(client, "victim@example.com")
    client.post(
        "/curator-assignments/", headers=auth_headers(victim_tokens["access_token"]), json={"group_id": 5},
    )
    PasswordResetTokenService(db_session).issue(victim.id)

    response = client.delete(f"/users/{victim.id}", headers=admin_headers)

    assert response.status_code == 204
    assert client.get(f"/users/{victim.id}", headers=admin_headers).status_code == 404
    assert db_session.query(RefreshToken).filter_by(user_id=victim.id).count() == 0
    assert db_session.query(PasswordResetToken).filter_by(user_id=victim.id).count() == 0
    assert db_session.query(CuratorGroupAssignment).filter_by(user_id=victim.id).count() == 0


def test_deleted_user_loses_access_immediately(client, db_session, admin_headers):
    victim = make_user(db_session, UserRoleEnum.curator, "evicted@example.com")
    tokens = login(client, "evicted@example.com")

    client.delete(f"/users/{victim.id}", headers=admin_headers)

    assert client.get("/auth/me", headers=auth_headers(tokens["access_token"])).status_code == 401
    assert client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401
    assert client.post("/auth/login", json={"login": "evicted", "password": PASSWORD}).status_code == 401


def test_deletion_is_audited_with_a_snapshot(client, db_session, admin_headers):
    victim = make_user(db_session, UserRoleEnum.dean, "snapshot@example.com")

    client.delete(f"/users/{victim.id}", headers=admin_headers)

    entries = client.get(f"/audit-log/by-target/user/{victim.id}", headers=admin_headers).json()
    deleted = [e for e in entries if e["action"] == "user_deleted"]
    assert len(deleted) == 1
    assert deleted[0]["details"] == {
        "login": "snapshot",
        "email": "snapshot@example.com",
        "first_name": "Test",
        "last_name": "User",
        "role": "dean",
    }


def test_audit_history_of_the_deleted_user_is_kept(client, db_session, admin_headers):
    victim = make_user(db_session, UserRoleEnum.curator, "remembered@example.com")
    login(client, "remembered@example.com")

    client.delete(f"/users/{victim.id}", headers=admin_headers)

    history = client.get(f"/audit-log/by-user/{victim.id}", headers=admin_headers).json()
    assert [e["action"] for e in history] == ["user_logged_in"]
    assert db_session.query(AuditLog).filter_by(user_id=victim.id).count() == 1


def test_email_and_login_can_be_reused_after_deletion(client, db_session, admin_headers):
    victim = make_user(db_session, UserRoleEnum.curator, "reuse@pnu.edu.ua")
    client.delete(f"/users/{victim.id}", headers=admin_headers)

    response = client.post("/users/", headers=admin_headers, json={
        "first_name": "New",
        "last_name": "Person",
        "email": "reuse@pnu.edu.ua",
        "password": "Welcome#2026",
        "role": "curator",
    })

    assert response.status_code == 201
    assert response.json()["login"] == "reuse"


def test_admin_cannot_delete_themselves(client, db_session):
    admin = make_user(db_session, UserRoleEnum.admin, "suicidal@example.com")
    headers = auth_headers(login(client, "suicidal@example.com")["access_token"])

    response = client.delete(f"/users/{admin.id}", headers=headers)

    assert response.status_code == 400
    assert client.get("/auth/me", headers=headers).status_code == 200


def test_deleting_an_unknown_user_returns_404(client, admin_headers):
    assert client.delete("/users/999999", headers=admin_headers).status_code == 404


def test_only_admin_can_delete_users(client, db_session):
    make_user(db_session, UserRoleEnum.curator, "wannabe@example.com")
    target = make_user(db_session, UserRoleEnum.curator, "target@example.com")
    headers = auth_headers(login(client, "wannabe@example.com")["access_token"])

    assert client.delete(f"/users/{target.id}", headers=headers).status_code == 403
    assert client.delete(f"/users/{target.id}").status_code in (401, 403)
