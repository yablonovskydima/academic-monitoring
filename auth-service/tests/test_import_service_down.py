import httpx
import pytest

from auth_service.models.user import UserRoleEnum
from helpers import auth_headers, login, make_user


@pytest.fixture(autouse=True)
def import_service_is_down(monkeypatch):
    def refuse(*args, **kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "get", refuse)


def test_dean_assignment_returns_503_when_import_service_is_down(client, db_session):
    make_user(db_session, UserRoleEnum.admin, "downadmin@example.com")
    dean = make_user(db_session, UserRoleEnum.dean, "downdean@example.com")
    headers = auth_headers(login(client, "downadmin@example.com")["access_token"])

    response = client.post("/dean-assignments/", headers=headers, json={"dean_user_id": dean.id, "faculty_id": 1})

    assert response.status_code == 503
    assert "unavailable" in response.json()["detail"]


def test_curator_assignment_returns_503_when_import_service_is_down(client, db_session):
    make_user(db_session, UserRoleEnum.curator, "downcurator@example.com")
    headers = auth_headers(login(client, "downcurator@example.com")["access_token"])

    response = client.post("/curator-assignments/", headers=headers, json={"group_id": 1})

    assert response.status_code == 503


def test_import_service_error_response_is_also_503(client, db_session, monkeypatch):
    def server_error(url, **kwargs):
        return httpx.Response(500, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", server_error)
    make_user(db_session, UserRoleEnum.curator, "down500@example.com")
    headers = auth_headers(login(client, "down500@example.com")["access_token"])

    response = client.post("/curator-assignments/", headers=headers, json={"group_id": 1})

    assert response.status_code == 503
