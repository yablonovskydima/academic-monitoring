from auth_service import bootstrap as bootstrap_module
from auth_service.models.user import UserRoleEnum
from helpers import make_user


def test_bootstrap_admin_is_a_noop_without_env_vars(db_session, monkeypatch):
    monkeypatch.setattr(bootstrap_module, "INITIAL_ADMIN_EMAIL", None)
    monkeypatch.setattr(bootstrap_module, "INITIAL_ADMIN_PASSWORD", None)

    result = bootstrap_module.bootstrap_admin(db_session)

    assert result is None


def test_bootstrap_admin_creates_an_admin_when_configured(db_session, monkeypatch):
    monkeypatch.setattr(bootstrap_module, "INITIAL_ADMIN_EMAIL", "bootstrap@example.com")
    monkeypatch.setattr(bootstrap_module, "INITIAL_ADMIN_PASSWORD", "Str0ng!Pass1")

    admin = bootstrap_module.bootstrap_admin(db_session)

    assert admin is not None
    assert admin.role == UserRoleEnum.admin
    assert admin.email == "bootstrap@example.com"
    assert admin.is_active is True


def test_bootstrap_admin_is_idempotent(db_session, monkeypatch):
    monkeypatch.setattr(bootstrap_module, "INITIAL_ADMIN_EMAIL", "bootstrap2@example.com")
    monkeypatch.setattr(bootstrap_module, "INITIAL_ADMIN_PASSWORD", "Str0ng!Pass1")

    first = bootstrap_module.bootstrap_admin(db_session)
    second = bootstrap_module.bootstrap_admin(db_session)

    assert first.id == second.id


def test_bootstrap_admin_does_not_override_an_existing_user_with_that_email(db_session, monkeypatch):
    existing_curator = make_user(db_session, UserRoleEnum.curator, "taken-by-curator@example.com")
    monkeypatch.setattr(bootstrap_module, "INITIAL_ADMIN_EMAIL", "taken-by-curator@example.com")
    monkeypatch.setattr(bootstrap_module, "INITIAL_ADMIN_PASSWORD", "Str0ng!Pass1")

    result = bootstrap_module.bootstrap_admin(db_session)

    assert result.id == existing_curator.id
    assert result.role == UserRoleEnum.curator
