import pytest

from auth_service.clients.import_service_client import ImportServiceClient
from auth_service.models.user import UserRoleEnum
from helpers import auth_headers, login, make_user


@pytest.fixture(autouse=True)
def fake_import_service(monkeypatch):
    monkeypatch.setattr(ImportServiceClient, "get_group", lambda self, group_id: {"id": group_id})
    monkeypatch.setattr(ImportServiceClient, "get_faculty", lambda self, faculty_id: {"id": faculty_id})


@pytest.fixture()
def admin_headers(client, db_session):
    make_user(db_session, UserRoleEnum.admin, "remover@example.com")
    return auth_headers(login(client, "remover@example.com")["access_token"])


def _audit(client, admin_headers, target_type, target_id, action):
    entries = client.get(f"/audit-log/by-target/{target_type}/{target_id}", headers=admin_headers).json()
    return [e for e in entries if e["action"] == action]


def test_curator_removes_own_assignment_and_it_is_audited(client, db_session, admin_headers):
    curator = make_user(db_session, UserRoleEnum.curator, "dropper@example.com")
    headers = auth_headers(login(client, "dropper@example.com")["access_token"])
    assignment = client.post("/curator-assignments/", headers=headers, json={"group_id": 8}).json()

    response = client.delete(f"/curator-assignments/{assignment['id']}", headers=headers)

    assert response.status_code == 204
    assert client.get("/curator-assignments/me", headers=headers).json() == []
    removed = _audit(client, admin_headers, "group", 8, "curator_group_assignment_removed")
    assert len(removed) == 1
    assert removed[0]["user_id"] == curator.id
    assert removed[0]["details"] == {"curator_user_id": curator.id}


def test_removing_a_missing_curator_assignment_returns_404(client, db_session):
    make_user(db_session, UserRoleEnum.curator, "ghosthunter@example.com")
    headers = auth_headers(login(client, "ghosthunter@example.com")["access_token"])

    assert client.delete("/curator-assignments/999999", headers=headers).status_code == 404


def test_admin_removes_dean_assignment_and_it_is_audited(client, db_session, admin_headers):
    dean = make_user(db_session, UserRoleEnum.dean, "oustedean@example.com")
    assignment = client.post(
        "/dean-assignments/", headers=admin_headers, json={"dean_user_id": dean.id, "faculty_id": 4},
    ).json()

    response = client.delete(f"/dean-assignments/{assignment['id']}", headers=admin_headers)

    assert response.status_code == 204
    dean_headers = auth_headers(login(client, "oustedean@example.com")["access_token"])
    assert client.get(f"/dean-assignments/{dean.id}", headers=dean_headers).json() == []
    removed = _audit(client, admin_headers, "faculty", 4, "dean_faculty_assignment_removed")
    assert len(removed) == 1
    assert removed[0]["details"] == {"dean_user_id": dean.id}


def test_removing_a_missing_dean_assignment_returns_404(client, admin_headers):
    assert client.delete("/dean-assignments/999999", headers=admin_headers).status_code == 404


def test_dean_assignment_requires_a_dean_and_rejects_duplicates(client, db_session, admin_headers):
    curator = make_user(db_session, UserRoleEnum.curator, "notadean@example.com")
    dean = make_user(db_session, UserRoleEnum.dean, "realdean@example.com")

    wrong_role = client.post(
        "/dean-assignments/", headers=admin_headers, json={"dean_user_id": curator.id, "faculty_id": 1},
    )
    first = client.post("/dean-assignments/", headers=admin_headers, json={"dean_user_id": dean.id, "faculty_id": 1})
    duplicate = client.post("/dean-assignments/", headers=admin_headers, json={"dean_user_id": dean.id, "faculty_id": 1})

    assert wrong_role.status_code == 400
    assert first.status_code == 201
    assert duplicate.status_code == 400


def test_curator_group_assignment_rejects_duplicates_and_unknown_groups(client, db_session, monkeypatch):
    make_user(db_session, UserRoleEnum.curator, "picky@example.com")
    headers = auth_headers(login(client, "picky@example.com")["access_token"])

    first = client.post("/curator-assignments/", headers=headers, json={"group_id": 2})
    duplicate = client.post("/curator-assignments/", headers=headers, json={"group_id": 2})
    monkeypatch.setattr(ImportServiceClient, "get_group", lambda self, group_id: None)
    unknown = client.post("/curator-assignments/", headers=headers, json={"group_id": 3})

    assert first.status_code == 201
    assert duplicate.status_code == 400
    assert unknown.status_code == 400
    assert client.get("/curator-assignments/me", headers=headers).json() == [2]
