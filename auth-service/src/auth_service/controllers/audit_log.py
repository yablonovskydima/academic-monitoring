from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from auth_service.database import get_db
from auth_service.dependencies import get_current_user
from auth_service.models.user import User
from auth_service.schemas.audit_log import AuditLogOut
from auth_service.services.audit_log_service import AuditLogService

router = APIRouter(prefix="/audit-log", tags=["audit_log"])

# TODO(RBAC): every endpoint in this file must be admin-only once

@router.get("/", response_model=list[AuditLogOut])
def get_audit_log(
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return AuditLogService(db).get_all(limit=limit, offset=offset)


@router.get("/by-user/{user_id}", response_model=list[AuditLogOut])
def get_audit_log_for_user(
    user_id: int,
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return AuditLogService(db).get_by_user(user_id, limit=limit, offset=offset)


@router.get("/by-target/{target_type}/{target_id}", response_model=list[AuditLogOut])
def get_audit_log_for_target(
    target_type: str,
    target_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return AuditLogService(db).get_by_target(target_type, target_id)
