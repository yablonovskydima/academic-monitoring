from datetime import timedelta

from auth_service.config import PASSWORD_RESET_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS
from auth_service.models.password_reset_token import PasswordResetToken
from auth_service.models.refresh_token import RefreshToken
from auth_service.models.user import UserRoleEnum
from auth_service.services.password_reset_token_service import PasswordResetTokenService
from auth_service.utils.clock import utc_now
from helpers import auth_headers, login, make_user


def _admin_headers(client, db_session):
    make_user(db_session, UserRoleEnum.admin, "pager@example.com")
    return auth_headers(login(client, "pager@example.com")["access_token"])


def test_audit_log_page_size_is_capped(client, db_session):
    headers = _admin_headers(client, db_session)

    for url in ("/audit-log/", "/audit-log/by-user/1", "/audit-log/by-target/user/1"):
        assert client.get(f"{url}?limit=501", headers=headers).status_code == 422
        assert client.get(f"{url}?limit=0", headers=headers).status_code == 422
        assert client.get(f"{url}?offset=-1", headers=headers).status_code == 422
        assert client.get(f"{url}?limit=500", headers=headers).status_code == 200


def test_audit_log_is_paginated(client, db_session):
    headers = _admin_headers(client, db_session)
    for _ in range(3):
        client.post("/auth/login", json={"login": "pager", "password": "Wrong#Pass1"})

    everything = client.get("/audit-log/", headers=headers).json()
    first_page = client.get("/audit-log/?limit=2", headers=headers).json()
    second_page = client.get("/audit-log/?limit=2&offset=2", headers=headers).json()

    assert len(first_page) == 2
    assert [e["id"] for e in first_page + second_page] == [e["id"] for e in everything][: len(first_page + second_page)]


def test_refresh_token_expiry_is_measured_in_utc(client, db_session):
    user = make_user(db_session, UserRoleEnum.curator, "clockwork@example.com")
    login(client, "clockwork@example.com")

    record = db_session.query(RefreshToken).filter_by(user_id=user.id).one()

    expected = utc_now() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    assert abs(record.expires_at - expected) < timedelta(minutes=1)


def test_password_reset_token_expiry_is_measured_in_utc(db_session):
    user = make_user(db_session, UserRoleEnum.curator, "resetclock@example.com")
    PasswordResetTokenService(db_session).issue(user.id)

    record = db_session.query(PasswordResetToken).filter_by(user_id=user.id).one()

    expected = utc_now() + timedelta(minutes=PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
    assert abs(record.expires_at - expected) < timedelta(minutes=1)
