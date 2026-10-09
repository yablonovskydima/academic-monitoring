from auth_shared import AuthEvent


def test_event_names_are_a_stable_contract():
    assert {e.name: e.value for e in AuthEvent} == {
        "user_deactivated": "auth.user.deactivated",
        "user_deleted": "auth.user.deleted",
        "user_role_changed": "auth.user.role_changed",
        "user_scopes_changed": "auth.user.scopes_changed",
        "session_revoked": "auth.session.revoked",
    }
