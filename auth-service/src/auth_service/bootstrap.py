from sqlalchemy.orm import Session

from auth_service.config import (
    INITIAL_ADMIN_EMAIL,
    INITIAL_ADMIN_FIRST_NAME,
    INITIAL_ADMIN_LAST_NAME,
    INITIAL_ADMIN_PASSWORD,
)
from auth_service.models.user import User, UserRoleEnum
from auth_service.schemas.audit_log import AuditLogCreate
from auth_service.schemas.user import UserCreate
from auth_service.services.audit_log_service import AuditLogService
from auth_service.services.user_service import UserService


def bootstrap_admin(db: Session) -> User | None:
    if not INITIAL_ADMIN_EMAIL or not INITIAL_ADMIN_PASSWORD:
        return None

    user_service = UserService(db)
    existing = user_service.get_by_email(INITIAL_ADMIN_EMAIL)
    if existing is not None:
        return existing

    admin = user_service.create(UserCreate(
        first_name=INITIAL_ADMIN_FIRST_NAME,
        last_name=INITIAL_ADMIN_LAST_NAME,
        email=INITIAL_ADMIN_EMAIL,
        password=INITIAL_ADMIN_PASSWORD,
        role=UserRoleEnum.admin,
    ))

    AuditLogService(db).log(AuditLogCreate(
        user_id=admin.id,
        action="admin_bootstrapped",
        target_type="user",
        target_id=admin.id,
    ))

    return admin
