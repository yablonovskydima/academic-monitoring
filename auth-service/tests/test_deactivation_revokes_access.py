from auth_service.models.user import UserRoleEnum
from helpers import auth_headers, login, make_user


def test_deactivated_admin_loses_admin_access_immediately(client, db_session):
    admin_a = make_user(db_session, UserRoleEnum.admin, "adminA@example.com")
    make_user(db_session, UserRoleEnum.admin, "adminB@example.com")
    tokens_a = login(client, "adminA@example.com")
    tokens_b = login(client, "adminB@example.com")

    deactivate = client.post(
        f"/users/{admin_a.id}/deactivate",
        headers=auth_headers(tokens_b["access_token"]),
    )
    assert deactivate.status_code == 200

    still_holding_old_token = client.get("/audit-log/", headers=auth_headers(tokens_a["access_token"]))
    assert still_holding_old_token.status_code == 401


def test_deactivated_user_loses_self_service_access_immediately(client, db_session):
    make_user(db_session, UserRoleEnum.admin, "adminC@example.com")
    admin_tokens = login(client, "adminC@example.com")
    curator = make_user(db_session, UserRoleEnum.curator, "curatorX@example.com")
    curator_tokens = login(client, "curatorX@example.com")

    client.post(f"/users/{curator.id}/deactivate", headers=auth_headers(admin_tokens["access_token"]))

    response = client.get("/auth/me", headers=auth_headers(curator_tokens["access_token"]))
    assert response.status_code == 401
