from auth_shared import AuthEvent
from sqlalchemy.orm import Session

from auth_service.models.user import User, UserRoleEnum
from auth_service.repositories.curator_group_assignment_repository import CuratorGroupAssignmentRepository
from auth_service.repositories.dean_faculty_assignment_repository import DeanFacultyAssignmentRepository
from auth_service.repositories.password_reset_token_repository import PasswordResetTokenRepository
from auth_service.repositories.refresh_token_repository import RefreshTokenRepository
from auth_service.repositories.user_repository import UserRepository
from auth_service.schemas.audit_log import AuditLogCreate
from auth_service.utils.notifications import send_account_credentials, send_login_changed
from auth_service.schemas.user import UserCreate, UserUpdate
from auth_service.utils.security import hash_password, verify_password
from auth_service.services.audit_log_service import AuditLogService
from auth_service.utils import events
from auth_service.utils.validators import validate_login


class UserService:
    def __init__(self, db: Session):
        self.repo = UserRepository(db)
        self.refresh_token_repo = RefreshTokenRepository(db)
        self.password_reset_token_repo = PasswordResetTokenRepository(db)
        self.curator_assignment_repo = CuratorGroupAssignmentRepository(db)
        self.dean_assignment_repo = DeanFacultyAssignmentRepository(db)
        self.audit_log_service = AuditLogService(db)

    def get_by_id(self, user_id: int) -> User | None:
        return self.repo.get_by_id(user_id)

    def get_by_email(self, email: str) -> User | None:
        return self.repo.get_by_email(email)

    def get_by_login(self, login: str) -> User | None:
        return self.repo.get_by_login(login)

    def list_users(
        self,
        role: UserRoleEnum | None = None,
        is_active: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[User]:
        return self.repo.list(role=role, is_active=is_active, limit=limit, offset=offset)

    def get_all(self) -> list[User]:
        return self.repo.get_all()

    def has_role(self, user_id: int, role: UserRoleEnum) -> bool:
        user = self.repo.get_by_id(user_id)
        return user is not None and user.role == role

    def create(self, data: UserCreate) -> User:
        login = validate_login(data.email.split("@")[0])
        if self.repo.get_by_login(login) is not None:
            raise ValueError(f"Login {login!r} (derived from email) is already taken")

        user = User(
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            login=login,
            hashed_password=hash_password(data.password),
            role=data.role,
        )
        return self.repo.save(user)

    def create_as_admin(self, actor_user_id: int, data: UserCreate) -> User:
        if self.repo.get_by_email(data.email) is not None:
            raise ValueError(f"Email {data.email} is already registered")

        user = self.create(data)

        self.audit_log_service.log(AuditLogCreate(
            user_id=actor_user_id,
            action="user_created",
            target_type="user",
            target_id=user.id,
            details={"role": user.role.value},
        ))

        send_account_credentials(user.email, user.login, data.password)

        return user

    def update_profile(self, actor_user_id: int, target_user_id: int, data: UserUpdate) -> User | None:
        user = self.repo.get_by_id(target_user_id)
        if user is None:
            return None

        changes = {}
        for field, value in data.model_dump(exclude_none=True).items():
            old_value = getattr(user, field)
            if old_value != value:
                changes[field] = {"from": old_value, "to": value}

        if "email" in changes:
            new_email = changes["email"]["to"]
            other = self.repo.get_by_email(new_email)
            if other is not None and other.id != user.id:
                raise ValueError(f"Email {new_email} is already registered")

            try:
                new_login = validate_login(new_email.split("@")[0])
            except ValueError as e:
                raise ValueError(f"Login derived from {new_email} is invalid: {e}") from e

            if new_login != user.login:
                owner = self.repo.get_by_login(new_login)
                if owner is not None and owner.id != user.id:
                    raise ValueError(f"Login {new_login!r} (derived from email) is already taken")
                changes["login"] = {"from": user.login, "to": new_login}

        if not changes:
            return user

        for field, change in changes.items():
            setattr(user, field, change["to"])
        user = self.repo.save(user)

        self.audit_log_service.log(AuditLogCreate(
            user_id=actor_user_id,
            action="user_updated",
            target_type="user",
            target_id=target_user_id,
            details=changes,
        ))

        if "login" in changes:
            send_login_changed(user.email, user.login)

        return user

    def authenticate(self, login: str, password: str) -> User | None:
        user = self.repo.get_by_login(login)
        if user is None or not user.is_active:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    def set_active(self, actor_user_id: int, target_user_id: int, is_active: bool) -> User | None:
        if not is_active and actor_user_id == target_user_id:
            raise ValueError("You cannot deactivate yourself")

        user = self.repo.get_by_id(target_user_id)
        if user is None:
            return None

        user.is_active = is_active
        user = self.repo.save(user)

        self.audit_log_service.log(AuditLogCreate(
            user_id=actor_user_id,
            action="user_activated" if is_active else "user_deactivated",
            target_type="user",
            target_id=target_user_id,
        ))

        if not is_active:
            events.publish_event(AuthEvent.user_deactivated, {"user_id": target_user_id})

        return user

    def set_role(self, actor_user_id: int, target_user_id: int, new_role: UserRoleEnum) -> User | None:
        if actor_user_id == target_user_id:
            raise ValueError("You cannot change your own role")

        user = self.repo.get_by_id(target_user_id)
        if user is None:
            return None
        if user.role == new_role:
            return user

        old_role = user.role
        user.role = new_role
        user = self.repo.save(user)

        self.curator_assignment_repo.delete_all_for_user(target_user_id)
        self.dean_assignment_repo.delete_all_for_user(target_user_id)
        self.refresh_token_repo.revoke_all_for_user(target_user_id)

        self.audit_log_service.log(AuditLogCreate(
            user_id=actor_user_id,
            action="user_role_changed",
            target_type="user",
            target_id=target_user_id,
            details={"from": old_role.value, "to": new_role.value},
        ))

        events.publish_event(AuthEvent.user_role_changed, {
            "user_id": target_user_id,
            "old_role": old_role.value,
            "new_role": new_role.value,
        })
        events.publish_event(AuthEvent.session_revoked, {"user_id": target_user_id, "session_id": None})

        return user

    def set_password(self, user_id: int, new_password: str) -> User | None:
        user = self.repo.get_by_id(user_id)
        if user is None:
            return None
        user.hashed_password = hash_password(new_password)
        return self.repo.save(user)

    def delete_user(self, actor_user_id: int, target_user_id: int) -> bool:
        if actor_user_id == target_user_id:
            raise ValueError("You cannot delete yourself")

        user = self.repo.get_by_id(target_user_id)
        if user is None:
            return False

        snapshot = {
            "login": user.login,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role.value,
        }

        self.refresh_token_repo.delete_all_for_user(target_user_id)
        self.password_reset_token_repo.delete_all_for_user(target_user_id)
        self.curator_assignment_repo.delete_all_for_user(target_user_id)
        self.dean_assignment_repo.delete_all_for_user(target_user_id)
        self.repo.delete(target_user_id)

        self.audit_log_service.log(AuditLogCreate(
            user_id=actor_user_id,
            action="user_deleted",
            target_type="user",
            target_id=target_user_id,
            details=snapshot,
        ))

        events.publish_event(AuthEvent.user_deleted, {"user_id": target_user_id})

        return True
