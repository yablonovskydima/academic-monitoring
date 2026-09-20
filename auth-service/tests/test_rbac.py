import pytest

from auth_service.clients.import_service_client import ImportServiceClient
from auth_service.models.user import UserRoleEnum
from helpers import auth_headers, login, make_user


@pytest.fixture(autouse=True)
def fake_import_service(monkeypatch):
    monkeypatch.setattr(ImportServiceClient, "get_group", lambda self, group_id: {"id": group_id})
    monkeypatch.setattr(ImportServiceClient, "get_faculty", lambda self, faculty_id: {"id": faculty_id})


def test_activate_user_requires_admin(client, db_session):
    make_user(db_session, UserRoleEnum.admin, "admin1@example.com")
    curator = make_user(db_session, UserRoleEnum.curator, "curator1@example.com")
    curator_tokens = login(client, "curator1@example.com")

    response = client.post(
        f"/users/{curator.id}/activate",
        headers=auth_headers(curator_tokens["access_token"]),
    )

    assert response.status_code == 403


def test_activate_user_without_a_token_is_rejected(client, db_session):
    curator = make_user(db_session, UserRoleEnum.curator, "curator2@example.com")

    response = client.post(f"/users/{curator.id}/activate")

    assert response.status_code in (401, 403)


def test_admin_can_deactivate_and_reactivate_a_user(client, db_session):
    make_user(db_session, UserRoleEnum.admin, "admin2@example.com")
    admin_tokens = login(client, "admin2@example.com")
    curator = make_user(db_session, UserRoleEnum.curator, "curator3@example.com")

    deactivated = client.post(
        f"/users/{curator.id}/deactivate",
        headers=auth_headers(admin_tokens["access_token"]),
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False

    reactivated = client.post(
        f"/users/{curator.id}/activate",
        headers=auth_headers(admin_tokens["access_token"]),
    )
    assert reactivated.status_code == 200
    assert reactivated.json()["is_active"] is True


def test_deactivate_unknown_user_returns_404(client, db_session):
    make_user(db_session, UserRoleEnum.admin, "admin3@example.com")
    admin_tokens = login(client, "admin3@example.com")

    response = client.post("/users/999999/deactivate", headers=auth_headers(admin_tokens["access_token"]))

    assert response.status_code == 404


def test_curator_can_assign_self_to_a_group(client, db_session):
    make_user(db_session, UserRoleEnum.curator, "curator4@example.com")
    tokens = login(client, "curator4@example.com")

    response = client.post(
        "/curator-assignments/",
        headers=auth_headers(tokens["access_token"]),
        json={"group_id": 1},
    )

    assert response.status_code == 201


def test_non_curator_cannot_assign_self_to_a_group(client, db_session):
    make_user(db_session, UserRoleEnum.dean, "dean1@example.com")
    tokens = login(client, "dean1@example.com")

    response = client.post(
        "/curator-assignments/",
        headers=auth_headers(tokens["access_token"]),
        json={"group_id": 1},
    )

    assert response.status_code == 403


def test_non_curator_cannot_read_curator_groups(client, db_session):
    make_user(db_session, UserRoleEnum.dean, "dean2@example.com")
    tokens = login(client, "dean2@example.com")

    response = client.get("/curator-assignments/me", headers=auth_headers(tokens["access_token"]))

    assert response.status_code == 403


def test_curator_cannot_remove_another_curators_assignment(client, db_session):
    make_user(db_session, UserRoleEnum.curator, "curatora@example.com")
    make_user(db_session, UserRoleEnum.curator, "curatorb@example.com")
    tokens_a = login(client, "curatora@example.com")
    tokens_b = login(client, "curatorb@example.com")

    created = client.post(
        "/curator-assignments/",
        headers=auth_headers(tokens_a["access_token"]),
        json={"group_id": 5},
    )
    assignment_id = created.json()["id"]

    response = client.delete(
        f"/curator-assignments/{assignment_id}",
        headers=auth_headers(tokens_b["access_token"]),
    )

    assert response.status_code == 403


def test_assign_dean_to_faculty_requires_admin(client, db_session):
    dean = make_user(db_session, UserRoleEnum.dean, "dean3@example.com")
    curator = make_user(db_session, UserRoleEnum.curator, "curator5@example.com")
    curator_tokens = login(client, "curator5@example.com")

    response = client.post(
        "/dean-assignments/",
        headers=auth_headers(curator_tokens["access_token"]),
        json={"dean_user_id": dean.id, "faculty_id": 1},
    )

    assert response.status_code == 403


def test_admin_can_assign_dean_to_faculty(client, db_session):
    make_user(db_session, UserRoleEnum.admin, "admin4@example.com")
    admin_tokens = login(client, "admin4@example.com")
    dean = make_user(db_session, UserRoleEnum.dean, "dean4@example.com")

    response = client.post(
        "/dean-assignments/",
        headers=auth_headers(admin_tokens["access_token"]),
        json={"dean_user_id": dean.id, "faculty_id": 1},
    )

    assert response.status_code == 201


def test_dean_can_read_their_own_faculties(client, db_session):
    make_user(db_session, UserRoleEnum.admin, "admin5@example.com")
    admin_tokens = login(client, "admin5@example.com")
    dean = make_user(db_session, UserRoleEnum.dean, "dean5@example.com")
    dean_tokens = login(client, "dean5@example.com")

    client.post(
        "/dean-assignments/",
        headers=auth_headers(admin_tokens["access_token"]),
        json={"dean_user_id": dean.id, "faculty_id": 2},
    )

    response = client.get(f"/dean-assignments/{dean.id}", headers=auth_headers(dean_tokens["access_token"]))

    assert response.status_code == 200
    assert response.json() == [2]


def test_dean_cannot_read_another_deans_faculties(client, db_session):
    dean_a = make_user(db_session, UserRoleEnum.dean, "deana@example.com")
    make_user(db_session, UserRoleEnum.dean, "deanb@example.com")
    tokens_b = login(client, "deanb@example.com")

    response = client.get(f"/dean-assignments/{dean_a.id}", headers=auth_headers(tokens_b["access_token"]))

    assert response.status_code == 403


def test_curator_cannot_read_dean_faculties_endpoint_at_all(client, db_session):
    curator = make_user(db_session, UserRoleEnum.curator, "curator6@example.com")
    tokens = login(client, "curator6@example.com")

    response = client.get(f"/dean-assignments/{curator.id}", headers=auth_headers(tokens["access_token"]))

    assert response.status_code == 403


def test_audit_log_requires_admin(client, db_session):
    make_user(db_session, UserRoleEnum.curator, "curator7@example.com")
    tokens = login(client, "curator7@example.com")

    all_logs = client.get("/audit-log/", headers=auth_headers(tokens["access_token"]))
    by_user = client.get("/audit-log/by-user/1", headers=auth_headers(tokens["access_token"]))
    by_target = client.get("/audit-log/by-target/user/1", headers=auth_headers(tokens["access_token"]))

    assert all_logs.status_code == 403
    assert by_user.status_code == 403
    assert by_target.status_code == 403


def test_admin_can_read_audit_log(client, db_session):
    make_user(db_session, UserRoleEnum.admin, "admin6@example.com")
    tokens = login(client, "admin6@example.com")

    response = client.get("/audit-log/", headers=auth_headers(tokens["access_token"]))

    assert response.status_code == 200
    assert isinstance(response.json(), list)
