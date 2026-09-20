from sqlalchemy.orm import Session

from auth_service.models.user import User, UserRoleEnum
from auth_service.schemas.audit_log import AuditLogCreate
from auth_service.schemas.auth import LoginRequest, TokenPair, UserRegister
from auth_service.schemas.user import UserCreate
from auth_service.security import create_access_token, verify_password
from auth_service.services.audit_log_service import AuditLogService
from auth_service.services.curator_group_assignment_service import CuratorGroupAssignmentService
from auth_service.services.dean_faculty_assignment_service import DeanFacultyAssignmentService
from auth_service.services.password_reset_token_service import PasswordResetTokenService
from auth_service.services.refresh_token_service import RefreshTokenService
from auth_service.services.user_service import UserService


class AuthService:
    DEFAULT_REGISTRATION_ROLE = UserRoleEnum.curator

    def __init__(self, db: Session):
        self.user_service = UserService(db)
        self.refresh_token_service = RefreshTokenService(db)
        self.password_reset_token_service = PasswordResetTokenService(db)
        self.audit_log_service = AuditLogService(db)
        self.curator_group_assignment_service = CuratorGroupAssignmentService(db)
        self.dean_faculty_assignment_service = DeanFacultyAssignmentService(db)

    def register(self, data: UserRegister) -> User:
        if self.user_service.get_by_email(data.email) is not None:
            raise ValueError(f"Email {data.email} is already registered")

        user = self.user_service.create(UserCreate(
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            password=data.password,
            role=self.DEFAULT_REGISTRATION_ROLE,
        ))

        self.audit_log_service.log(AuditLogCreate(
            user_id=user.id,
            action="user_registered",
        ))

        return user

    def login(self, data: LoginRequest) -> TokenPair:
        user = self.user_service.authenticate(data.login, data.password)
        if user is None:
            self.audit_log_service.log(AuditLogCreate(
                action="login_failed",
                details={"login": data.login},
            ))
            raise ValueError("Invalid login or password")

        self.audit_log_service.log(AuditLogCreate(
            user_id=user.id,
            action="user_logged_in",
        ))

        return self._issue_pair(user)

    def refresh(self, raw_refresh_token: str) -> TokenPair:
        record = self.refresh_token_service.get_valid(raw_refresh_token)
        if record is None:
            raise ValueError("Invalid or expired refresh token")

        user = self.user_service.get_by_id(record.user_id)
        if user is None or not user.is_active:
            raise ValueError("Invalid or expired refresh token")

        self.refresh_token_service.revoke(raw_refresh_token)

        self.audit_log_service.log(AuditLogCreate(
            user_id=user.id,
            action="token_refreshed",
        ))

        return self._issue_pair(user)

    def logout(self, raw_refresh_token: str) -> None:
        record = self.refresh_token_service.get_valid(raw_refresh_token)
        self.refresh_token_service.revoke(raw_refresh_token)

        self.audit_log_service.log(AuditLogCreate(
            user_id=record.user_id if record else None,
            action="user_logged_out",
        ))

    def revoke_all_sessions(self, user_id: int) -> None:
        self.refresh_token_service.revoke_all_for_user(user_id)

        self.audit_log_service.log(AuditLogCreate(
            user_id=user_id,
            action="all_sessions_revoked",
        ))

    def change_password(self, user: User, current_password: str, new_password: str) -> None:
        if not verify_password(current_password, user.hashed_password):
            raise ValueError("Current password is incorrect")

        self.user_service.set_password(user.id, new_password)
        self.refresh_token_service.revoke_all_for_user(user.id)

        self.audit_log_service.log(AuditLogCreate(
            user_id=user.id,
            action="password_changed",
        ))

    def request_password_reset(self, login: str) -> None:
        user = self.user_service.get_by_login(login)
        if user is None:
            return

        issued = self.password_reset_token_service.issue(user.id)

        # TODO: send `issued.raw_token` via notification-service
        # (email with a reset link) once that service exists. For
        # now just log it so the flow is testable end-to-end locally.
        print(f"[password reset] token for user {user.id} ({user.login}): {issued.raw_token}")

    def reset_password(self, raw_token: str, new_password: str) -> None:
        record = self.password_reset_token_service.get_valid(raw_token)
        if record is None:
            raise ValueError("Invalid or expired reset token")

        self.user_service.set_password(record.user_id, new_password)
        self.password_reset_token_service.mark_used(record.id)
        self.refresh_token_service.revoke_all_for_user(record.user_id)

        self.audit_log_service.log(AuditLogCreate(
            user_id=record.user_id,
            action="password_reset",
        ))

    def _issue_pair(self, user: User) -> TokenPair:
        group_ids = self.curator_group_assignment_service.get_group_ids_for_user(user.id)
        faculty_ids = self.dean_faculty_assignment_service.get_faculty_ids_for_user(user.id)

        access_token = create_access_token(user.id, user.role.value, group_ids, faculty_ids)
        issued_refresh = self.refresh_token_service.issue(user.id)

        return TokenPair(
            access_token=access_token,
            refresh_token=issued_refresh.raw_token,
        )
