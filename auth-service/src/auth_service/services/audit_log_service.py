from sqlalchemy.orm import Session

from auth_service.models.audit_log import AuditLog
from auth_service.repositories.audit_log_repository import AuditLogRepository
from auth_service.schemas.audit_log import AuditLogCreate


class AuditLogService:
    """
    See CLAUDE.md / models/audit_log.py — this is the accountability
    trail for the whole platform. Business logic anywhere that reads
    sensitive student data or changes something another user relies
    on should call `log(...)` here, not skip it.
    """

    def __init__(self, db: Session):
        self.repo = AuditLogRepository(db)

    def log(self, data: AuditLogCreate) -> AuditLog:
        entry = AuditLog(
            user_id=data.user_id,
            action=data.action,
            target_type=data.target_type,
            target_id=data.target_id,
            details=data.details,
        )
        return self.repo.save(entry)

    def get_all(self, limit: int = 100, offset: int = 0) -> list[AuditLog]:
        return self.repo.get_all(limit=limit, offset=offset)

    def get_by_user(self, user_id: int, limit: int = 100, offset: int = 0) -> list[AuditLog]:
        return self.repo.get_by_user(user_id, limit=limit, offset=offset)

    def get_by_target(self, target_type: str, target_id: int) -> list[AuditLog]:
        return self.repo.get_by_target(target_type, target_id)
