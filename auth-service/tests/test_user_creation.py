import pytest

from auth_service.models.user import UserRoleEnum
from helpers import auth_headers, login, make_user


@pytest.fixture()
def admin_headers(client, db_session):
    make_user(db_session, UserRoleEnum.admin, "creator@example.com")
    return auth_headers(login(client, "creator@example.com")["access_token"])


def _new_user(**overrides):
    body = {
        "first_name": "Ivan",
        "last_name": "Petrenko",
        "email": "ivan.petrenko@pnu.edu.ua",
        "password": "Welcome#2026",
        "role": "curator",
    }
    body.update(overrides)
    return body


def test_public_registration_no_longer_exists(client):
    response = client.post("/auth/register", json=_new_user(confirm_password="Welcome#2026"))

    assert response.status_code in (404, 405)


def test_admin_creates_a_user_who_can_log_in_with_the_given_password(client, admin_headers):
    response = client.post("/users/", headers=admin_headers, json=_new_user(role="dean"))

    assert response.status_code == 201, response.text
    assert response.json()["role"] == "dean"
    assert response.json()["login"] == "ivan.petrenko"
    assert "password" not in response.json()

    tokens = client.post("/auth/login", json={"login": "ivan.petrenko", "password": "Welcome#2026"})
    assert tokens.status_code == 200


def test_credentials_are_sent_to_the_users_email(client, admin_headers, capsys):
    client.post("/users/", headers=admin_headers, json=_new_user())

    out = capsys.readouterr().out
    assert "ivan.petrenko@pnu.edu.ua" in out
    assert "login=ivan.petrenko" in out
    assert "password=Welcome#2026" in out


def test_second_allowed_domain_is_accepted(client, admin_headers):
    response = client.post("/users/", headers=admin_headers, json=_new_user(email="olha@cnu.edu.ua"))

    assert response.status_code == 201


def test_email_outside_allowed_domains_is_rejected(client, admin_headers):
    response = client.post("/users/", headers=admin_headers, json=_new_user(email="ivan@gmail.com"))

    assert response.status_code == 422


def test_weak_password_is_rejected(client, admin_headers):
    response = client.post("/users/", headers=admin_headers, json=_new_user(password="weak"))

    assert response.status_code == 422


def test_unknown_role_is_rejected(client, admin_headers):
    response = client.post("/users/", headers=admin_headers, json=_new_user(role="superuser"))

    assert response.status_code == 422


def test_duplicate_email_is_rejected(client, admin_headers):
    client.post("/users/", headers=admin_headers, json=_new_user())

    response = client.post("/users/", headers=admin_headers, json=_new_user())

    assert response.status_code == 409


def test_same_login_on_another_domain_is_rejected(client, admin_headers):
    client.post("/users/", headers=admin_headers, json=_new_user(email="ivan@pnu.edu.ua"))

    response = client.post("/users/", headers=admin_headers, json=_new_user(email="ivan@cnu.edu.ua"))

    assert response.status_code == 409


def test_only_admin_can_create_users(client, db_session):
    make_user(db_session, UserRoleEnum.curator, "notadmin@example.com")
    headers = auth_headers(login(client, "notadmin@example.com")["access_token"])

    response = client.post("/users/", headers=headers, json=_new_user())

    assert response.status_code == 403


def test_creation_without_a_token_is_rejected(client):
    response = client.post("/users/", json=_new_user())

    assert response.status_code in (401, 403)


def test_user_creation_is_audited(client, admin_headers):
    created = client.post("/users/", headers=admin_headers, json=_new_user(role="dean")).json()

    entries = client.get(f"/audit-log/by-target/user/{created['id']}", headers=admin_headers).json()

    made = [e for e in entries if e["action"] == "user_created"]
    assert len(made) == 1
    assert made[0]["details"] == {"role": "dean"}


def test_admin_can_edit_name_and_email(client, admin_headers):
    created = client.post("/users/", headers=admin_headers, json=_new_user()).json()

    response = client.patch(
        f"/users/{created['id']}",
        headers=admin_headers,
        json={"first_name": "Yaroslav", "email": "yaroslav@cnu.edu.ua"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["first_name"] == "Yaroslav"
    assert body["last_name"] == "Petrenko"
    assert body["email"] == "yaroslav@cnu.edu.ua"
    assert body["login"] == "yaroslav"


def test_profile_edit_is_audited_with_old_and_new_values(client, admin_headers):
    created = client.post("/users/", headers=admin_headers, json=_new_user()).json()

    client.patch(f"/users/{created['id']}", headers=admin_headers, json={"last_name": "Shevchenko"})

    entries = client.get(f"/audit-log/by-target/user/{created['id']}", headers=admin_headers).json()
    edits = [e for e in entries if e["action"] == "user_updated"]
    assert len(edits) == 1
    assert edits[0]["details"] == {"last_name": {"from": "Petrenko", "to": "Shevchenko"}}


def test_unchanged_values_produce_no_audit_entry(client, admin_headers):
    created = client.post("/users/", headers=admin_headers, json=_new_user()).json()

    client.patch(f"/users/{created['id']}", headers=admin_headers, json={"last_name": "Petrenko"})

    entries = client.get(f"/audit-log/by-target/user/{created['id']}", headers=admin_headers).json()
    assert not [e for e in entries if e["action"] == "user_updated"]


def test_edit_rejects_empty_body_bad_domain_and_bad_name(client, admin_headers):
    created = client.post("/users/", headers=admin_headers, json=_new_user()).json()
    url = f"/users/{created['id']}"

    assert client.patch(url, headers=admin_headers, json={}).status_code == 422
    assert client.patch(url, headers=admin_headers, json={"email": "x@gmail.com"}).status_code == 422
    assert client.patch(url, headers=admin_headers, json={"first_name": "Yasha Lava 2"}).status_code == 422


def test_edit_rejects_an_email_that_belongs_to_someone_else(client, admin_headers):
    client.post("/users/", headers=admin_headers, json=_new_user(email="first@pnu.edu.ua"))
    second = client.post("/users/", headers=admin_headers, json=_new_user(email="second@pnu.edu.ua")).json()

    response = client.patch(f"/users/{second['id']}", headers=admin_headers, json={"email": "first@pnu.edu.ua"})

    assert response.status_code == 409


def test_edit_unknown_user_returns_404(client, admin_headers):
    response = client.patch("/users/999999", headers=admin_headers, json={"first_name": "Ghost"})

    assert response.status_code == 404


def test_users_cannot_edit_their_own_profile(client, db_session):
    user = make_user(db_session, UserRoleEnum.curator, "selfedit@example.com")
    headers = auth_headers(login(client, "selfedit@example.com")["access_token"])

    response = client.patch(f"/users/{user.id}", headers=headers, json={"first_name": "Yasha"})

    assert response.status_code == 403


def test_login_follows_the_email_change(client, admin_headers, capsys):
    created = client.post("/users/", headers=admin_headers, json=_new_user()).json()
    tokens = client.post("/auth/login", json={"login": "ivan.petrenko", "password": "Welcome#2026"}).json()

    client.patch(f"/users/{created['id']}", headers=admin_headers, json={"email": "yaroslav@pnu.edu.ua"})

    assert client.post("/auth/login", json={"login": "ivan.petrenko", "password": "Welcome#2026"}).status_code == 401
    assert client.post("/auth/login", json={"login": "yaroslav", "password": "Welcome#2026"}).status_code == 200
    assert client.get("/auth/me", headers=auth_headers(tokens["access_token"])).json()["login"] == "yaroslav"
    assert "[login changed] to yaroslav@pnu.edu.ua: new login=yaroslav" in capsys.readouterr().out


def test_changing_only_the_domain_keeps_the_login(client, admin_headers, capsys):
    created = client.post("/users/", headers=admin_headers, json=_new_user(email="ivan@pnu.edu.ua")).json()
    capsys.readouterr()

    response = client.patch(f"/users/{created['id']}", headers=admin_headers, json={"email": "ivan@cnu.edu.ua"})

    assert response.status_code == 200
    assert response.json()["login"] == "ivan"
    assert "[login changed]" not in capsys.readouterr().out


def test_email_change_is_rejected_when_the_new_login_is_taken(client, admin_headers):
    client.post("/users/", headers=admin_headers, json=_new_user(email="taken@pnu.edu.ua"))
    other = client.post("/users/", headers=admin_headers, json=_new_user(email="other@pnu.edu.ua")).json()

    response = client.patch(f"/users/{other['id']}", headers=admin_headers, json={"email": "taken@cnu.edu.ua"})

    assert response.status_code == 409
    unchanged = client.post("/auth/login", json={"login": "other", "password": "Welcome#2026"})
    assert unchanged.status_code == 200


def test_email_change_is_rejected_when_the_derived_login_is_invalid(client, admin_headers):
    created = client.post("/users/", headers=admin_headers, json=_new_user()).json()

    response = client.patch(f"/users/{created['id']}", headers=admin_headers, json={"email": "ab@pnu.edu.ua"})

    assert response.status_code == 409
    assert "invalid" in response.json()["detail"]


def test_login_change_is_audited(client, admin_headers):
    created = client.post("/users/", headers=admin_headers, json=_new_user()).json()

    client.patch(f"/users/{created['id']}", headers=admin_headers, json={"email": "newname@pnu.edu.ua"})

    entries = client.get(f"/audit-log/by-target/user/{created['id']}", headers=admin_headers).json()
    edit = [e for e in entries if e["action"] == "user_updated"][0]
    assert edit["details"]["login"] == {"from": "ivan.petrenko", "to": "newname"}
