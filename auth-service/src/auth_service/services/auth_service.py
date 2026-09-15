from sqlalchemy.orm import Session

from auth_service.models.user import User, UserRoleEnum
from auth_service.schemas.auth import LoginRequest, TokenPair, UserRegister
from auth_service.schemas.user import UserCreate
from auth_service.security import create_access_token
from auth_service.services.refresh_token_service import RefreshTokenService
from auth_service.services.user_service import UserService


class AuthService:
    """
    Orchestrates login/register/refresh/logout across UserService and
    RefreshTokenService, and issues JWT access tokens. This is the
    authentication layer only — role-based access control (which
    endpoints a role may call) is a separate, not-yet-built layer,
    see CLAUDE.md.
    """

    DEFAULT_REGISTRATION_ROLE = UserRoleEnum.curator

    def __init__(self, db: Session):
        self.user_service = UserService(db)
        self.refresh_token_service = RefreshTokenService(db)

    def register(self, data: UserRegister) -> User:
        if self.user_service.get_by_email(data.email) is not None:
            raise ValueError(f"Email {data.email} is already registered")

        return self.user_service.create(UserCreate(
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            password=data.password,
            role=self.DEFAULT_REGISTRATION_ROLE,
        ))

    def login(self, data: LoginRequest) -> TokenPair:
        user = self.user_service.authenticate(data.login, data.password)
        if user is None:
            raise ValueError("Invalid login or password")

        return self._issue_pair(user)

    def refresh(self, raw_refresh_token: str) -> TokenPair:
        record = self.refresh_token_service.get_valid(raw_refresh_token)
        if record is None:
            raise ValueError("Invalid or expired refresh token")

        user = self.user_service.get_by_id(record.user_id)
        if user is None or not user.is_active:
            raise ValueError("Invalid or expired refresh token")

        # Rotate: the old refresh token dies the moment it's used.
        # Reuse of an already-rotated token would be a signal of
        # theft — worth alerting on once this is wired to audit_log.
        self.refresh_token_service.revoke(raw_refresh_token)

        return self._issue_pair(user)

    def logout(self, raw_refresh_token: str) -> None:
        self.refresh_token_service.revoke(raw_refresh_token)

    def _issue_pair(self, user: User) -> TokenPair:
        access_token = create_access_token(user.id, user.role.value)
        issued_refresh = self.refresh_token_service.issue(user.id)

        return TokenPair(
            access_token=access_token,
            refresh_token=issued_refresh.raw_token,
        )
