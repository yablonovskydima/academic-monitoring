from auth_service.models.user import UserRoleEnum
from auth_service.services.password_reset_token_service import PasswordResetTokenService
from helpers import PASSWORD, auth_headers, login, make_user


def test_register_creates_a_curator(client):
    response = client.post("/auth/register", json={
        "first_name": "Petro",
        "last_name": "Kovalenko",
        "email": "petro@example.com",
        "password": PASSWORD,
        "confirm_password": PASSWORD,
    })

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["role"] == "curator"
    assert body["is_active"] is True


def test_register_rejects_duplicate_email(client, db_session):
    make_user(db_session, UserRoleEnum.curator, "taken@example.com")

    response = client.post("/auth/register", json={
        "first_name": "Petro",
        "last_name": "Kovalenko",
        "email": "taken@example.com",
        "password": PASSWORD,
        "confirm_password": PASSWORD,
    })

    assert response.status_code == 409


def test_register_rejects_mismatched_passwords(client):
    response = client.post("/auth/register", json={
        "first_name": "Petro",
        "last_name": "Kovalenko",
        "email": "petro2@example.com",
        "password": PASSWORD,
        "confirm_password": "SomethingElse1!",
    })

    assert response.status_code == 422


def test_login_with_correct_credentials_returns_token_pair(client, db_session):
    make_user(db_session, UserRoleEnum.curator, "curator@example.com")

    tokens = login(client, "curator@example.com")

    assert tokens["access_token"]
    assert tokens["refresh_token"]


def test_login_with_wrong_password_is_rejected(client, db_session):
    make_user(db_session, UserRoleEnum.curator, "curator2@example.com")

    response = client.post("/auth/login", json={"login": "curator2", "password": "WrongPass1!"})

    assert response.status_code == 401


def test_login_with_inactive_user_is_rejected(client, db_session):
    user = make_user(db_session, UserRoleEnum.curator, "inactive@example.com")
    user.is_active = False
    db_session.add(user)
    db_session.commit()

    response = client.post("/auth/login", json={"login": "inactive", "password": PASSWORD})

    assert response.status_code == 401


def test_refresh_rotates_the_token_and_invalidates_the_old_one(client, db_session):
    make_user(db_session, UserRoleEnum.curator, "refresh@example.com")
    tokens = login(client, "refresh@example.com")

    refreshed = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    assert refreshed.json()["refresh_token"] != tokens["refresh_token"]

    reused = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reused.status_code == 401


def test_logout_revokes_the_refresh_token(client, db_session):
    make_user(db_session, UserRoleEnum.curator, "logout@example.com")
    tokens = login(client, "logout@example.com")

    response = client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert response.status_code == 204

    reused = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reused.status_code == 401


def test_revoke_all_sessions_invalidates_every_refresh_token(client, db_session):
    make_user(db_session, UserRoleEnum.curator, "multi@example.com")
    session_a = login(client, "multi@example.com")
    session_b = login(client, "multi@example.com")

    response = client.post("/auth/revoke-all", headers=auth_headers(session_a["access_token"]))
    assert response.status_code == 204

    reused = client.post("/auth/refresh", json={"refresh_token": session_b["refresh_token"]})
    assert reused.status_code == 401


def test_change_password_requires_correct_current_password(client, db_session):
    make_user(db_session, UserRoleEnum.curator, "change@example.com")
    tokens = login(client, "change@example.com")

    response = client.post(
        "/auth/change-password",
        headers=auth_headers(tokens["access_token"]),
        json={
            "current_password": "WrongCurrent1!",
            "new_password": "NewStr0ng!Pass",
            "confirm_new_password": "NewStr0ng!Pass",
        },
    )

    assert response.status_code == 400


def test_change_password_updates_credentials_and_revokes_existing_sessions(client, db_session):
    make_user(db_session, UserRoleEnum.curator, "change2@example.com")
    tokens = login(client, "change2@example.com")

    response = client.post(
        "/auth/change-password",
        headers=auth_headers(tokens["access_token"]),
        json={
            "current_password": PASSWORD,
            "new_password": "NewStr0ng!Pass",
            "confirm_new_password": "NewStr0ng!Pass",
        },
    )
    assert response.status_code == 204

    old_session_refresh = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert old_session_refresh.status_code == 401

    relogin = client.post("/auth/login", json={"login": "change2", "password": "NewStr0ng!Pass"})
    assert relogin.status_code == 200


def test_forgot_password_returns_generic_response_for_unknown_login(client):
    response = client.post("/auth/forgot-password", json={"login": "nobody-here"})
    assert response.status_code == 202


def test_reset_password_with_valid_token_changes_the_password(client, db_session):
    user = make_user(db_session, UserRoleEnum.curator, "reset@example.com")
    issued = PasswordResetTokenService(db_session).issue(user.id)

    response = client.post("/auth/reset-password", json={
        "token": issued.raw_token,
        "new_password": "NewStr0ng!Pass",
        "confirm_new_password": "NewStr0ng!Pass",
    })
    assert response.status_code == 204

    relogin = client.post("/auth/login", json={"login": "reset", "password": "NewStr0ng!Pass"})
    assert relogin.status_code == 200


def test_reset_password_token_cannot_be_reused(client, db_session):
    user = make_user(db_session, UserRoleEnum.curator, "reset2@example.com")
    issued = PasswordResetTokenService(db_session).issue(user.id)

    first = client.post("/auth/reset-password", json={
        "token": issued.raw_token,
        "new_password": "NewStr0ng!Pass",
        "confirm_new_password": "NewStr0ng!Pass",
    })
    assert first.status_code == 204

    second = client.post("/auth/reset-password", json={
        "token": issued.raw_token,
        "new_password": "AnotherStr0ng!Pass",
        "confirm_new_password": "AnotherStr0ng!Pass",
    })
    assert second.status_code == 400


def test_me_returns_the_authenticated_user(client, db_session):
    make_user(db_session, UserRoleEnum.curator, "myself@example.com")
    tokens = login(client, "myself@example.com")

    response = client.get("/auth/me", headers=auth_headers(tokens["access_token"]))

    assert response.status_code == 200
    assert response.json()["email"] == "myself@example.com"


def test_me_without_a_token_is_rejected(client):
    response = client.get("/auth/me")
    assert response.status_code in (401, 403)
