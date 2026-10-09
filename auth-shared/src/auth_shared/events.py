import enum


class AuthEvent(str, enum.Enum):
    user_deactivated = "auth.user.deactivated"
    user_deleted = "auth.user.deleted"
    user_role_changed = "auth.user.role_changed"
    user_scopes_changed = "auth.user.scopes_changed"
    session_revoked = "auth.session.revoked"
