from auth_service.clients.import_service_client import ImportServiceClient
from auth_service.models.user import UserRoleEnum
from auth_service.services.curator_group_assignment_service import CuratorGroupAssignmentService
from helpers import auth_headers, login, make_user


def _admin(client, db_session, email="boss@example.com"):
    admin = make_user(db_session, UserRoleEnum.admin, email)
    return admin, auth_headers(login(client, email)["access_token"])


def test_admin_cannot_deactivate_themselves(client, db_session):
    admin, headers = _admin(client, db_session)

    response = client.post(f"/users/{admin.id}/deactivate", headers=headers)

    assert response.status_code == 400
    assert client.get("/auth/me", headers=headers).status_code == 200


def test_admin_can_change_another_users_role(client, db_session):
    _, headers = _admin(client, db_session)
    curator = make_user(db_session, UserRoleEnum.curator, "future.dean@example.com")

    response = client.post(f"/users/{curator.id}/role", headers=headers, json={"role": "dean"})

    assert response.status_code == 200
    assert response.json()["role"] == "dean"


def test_admin_cannot_change_their_own_role(client, db_session):
    admin, headers = _admin(client, db_session)

    response = client.post(f"/users/{admin.id}/role", headers=headers, json={"role": "curator"})

    assert response.status_code == 400
    assert client.get("/auth/me", headers=headers).json()["role"] == "admin"


def test_non_admin_cannot_change_roles(client, db_session):
    make_user(db_session, UserRoleEnum.curator, "plain@example.com")
    other = make_user(db_session, UserRoleEnum.curator, "other@example.com")
    headers = auth_headers(login(client, "plain@example.com")["access_token"])

    response = client.post(f"/users/{other.id}/role", headers=headers, json={"role": "admin"})

    assert response.status_code == 403


def test_change_role_of_unknown_user_returns_404(client, db_session):
    _, headers = _admin(client, db_session)

    response = client.post("/users/999999/role", headers=headers, json={"role": "dean"})

    assert response.status_code == 404


def test_change_role_rejects_unknown_role(client, db_session):
    _, headers = _admin(client, db_session)
    curator = make_user(db_session, UserRoleEnum.curator, "badrole@example.com")

    response = client.post(f"/users/{curator.id}/role", headers=headers, json={"role": "superuser"})

    assert response.status_code == 422


def test_role_change_revokes_sessions_and_clears_old_assignments(client, db_session, monkeypatch):
    monkeypatch.setattr(ImportServiceClient, "get_group", lambda self, group_id: {"id": group_id})
    _, admin_headers = _admin(client, db_session)
    curator = make_user(db_session, UserRoleEnum.curator, "demoted@example.com")
    curator_tokens = login(client, "demoted@example.com")
    client.post(
        "/curator-assignments/",
        headers=auth_headers(curator_tokens["access_token"]),
        json={"group_id": 3},
    )

    client.post(f"/users/{curator.id}/role", headers=admin_headers, json={"role": "dean"})

    assert client.get("/auth/me", headers=auth_headers(curator_tokens["access_token"])).status_code == 401
    assert client.post("/auth/refresh", json={"refresh_token": curator_tokens["refresh_token"]}).status_code == 401

    relogin = login(client, "demoted@example.com")
    me = client.get("/auth/me", headers=auth_headers(relogin["access_token"]))
    assert me.json()["role"] == "dean"
    assert CuratorGroupAssignmentService(db_session).get_group_ids_for_user(curator.id) == []


def test_role_change_is_audited(client, db_session):
    admin, headers = _admin(client, db_session)
    curator = make_user(db_session, UserRoleEnum.curator, "audited@example.com")

    client.post(f"/users/{curator.id}/role", headers=headers, json={"role": "dean"})

    entries = client.get(f"/audit-log/by-target/user/{curator.id}", headers=headers).json()
    changed = [e for e in entries if e["action"] == "user_role_changed"]
    assert len(changed) == 1
    assert changed[0]["user_id"] == admin.id
    assert changed[0]["details"] == {"from": "curator", "to": "dean"}
