import pytest

from auth_service.models.user import UserRoleEnum
from helpers import auth_headers, login, make_user


@pytest.fixture()
def admin_headers(client, db_session):
    make_user(db_session, UserRoleEnum.admin, "lister@example.com")
    return auth_headers(login(client, "lister@example.com")["access_token"])


@pytest.fixture()
def populated(db_session):
    make_user(db_session, UserRoleEnum.curator, "curator.one@example.com")
    make_user(db_session, UserRoleEnum.curator, "curator.two@example.com")
    inactive = make_user(db_session, UserRoleEnum.dean, "dean.one@example.com")
    inactive.is_active = False
    db_session.add(inactive)
    db_session.commit()


def test_admin_lists_all_users(client, admin_headers, populated):
    response = client.get("/users/", headers=admin_headers)

    assert response.status_code == 200
    assert [u["login"] for u in response.json()] == ["lister", "curator.one", "curator.two", "dean.one"]
    assert "hashed_password" not in response.json()[0]


def test_list_can_filter_by_role_and_activity(client, admin_headers, populated):
    curators = client.get("/users/?role=curator", headers=admin_headers).json()
    inactive = client.get("/users/?is_active=false", headers=admin_headers).json()

    assert [u["login"] for u in curators] == ["curator.one", "curator.two"]
    assert [u["login"] for u in inactive] == ["dean.one"]


def test_list_is_paginated(client, admin_headers, populated):
    page = client.get("/users/?limit=2&offset=1", headers=admin_headers).json()

    assert [u["login"] for u in page] == ["curator.one", "curator.two"]


def test_list_page_size_is_capped(client, admin_headers):
    assert client.get("/users/?limit=501", headers=admin_headers).status_code == 422
    assert client.get("/users/?limit=0", headers=admin_headers).status_code == 422
    assert client.get("/users/?offset=-1", headers=admin_headers).status_code == 422
    assert client.get("/users/?limit=500", headers=admin_headers).status_code == 200


def test_list_rejects_unknown_role_filter(client, admin_headers):
    assert client.get("/users/?role=superuser", headers=admin_headers).status_code == 422


def test_admin_gets_a_user_by_id(client, admin_headers, populated, db_session):
    target = make_user(db_session, UserRoleEnum.curator, "findme@example.com")

    response = client.get(f"/users/{target.id}", headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["email"] == "findme@example.com"


def test_get_unknown_user_returns_404(client, admin_headers):
    assert client.get("/users/999999", headers=admin_headers).status_code == 404


def test_non_admin_cannot_list_or_read_users(client, db_session):
    user = make_user(db_session, UserRoleEnum.curator, "nosy@example.com")
    headers = auth_headers(login(client, "nosy@example.com")["access_token"])

    assert client.get("/users/", headers=headers).status_code == 403
    assert client.get(f"/users/{user.id}", headers=headers).status_code == 403


def test_listing_without_a_token_is_rejected(client):
    assert client.get("/users/").status_code in (401, 403)
