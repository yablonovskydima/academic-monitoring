from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from auth_service.database import get_db
from auth_service.dependencies import require_role
from auth_service.models.user import User, UserRoleEnum
from auth_service.schemas.audit_log import AuditLogOut
from auth_service.services.audit_log_service import AuditLogService

router = APIRouter(prefix="/audit-log", tags=["audit_log"])


@router.get("/", response_model=list[AuditLogOut])
def get_audit_log(
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(require_role(UserRoleEnum.admin)),
    db: Session = Depends(get_db),
):
    return AuditLogService(db).get_all(limit=limit, offset=offset)


@router.get("/by-user/{user_id}", response_model=list[AuditLogOut])
def get_audit_log_for_user(
    user_id: int,
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(require_role(UserRoleEnum.admin)),
    db: Session = Depends(get_db),
):
    return AuditLogService(db).get_by_user(user_id, limit=limit, offset=offset)


@router.get("/by-target/{target_type}/{target_id}", response_model=list[AuditLogOut])
def get_audit_log_for_target(
    target_type: str,
    target_id: int,
    current_user: User = Depends(require_role(UserRoleEnum.admin)),
    db: Session = Depends(get_db),
):
    return AuditLogService(db).get_by_target(target_type, target_id)
