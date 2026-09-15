from sqlalchemy import select
from sqlalchemy.orm import Session

from auth_service.models.audit_log import AuditLog


class AuditLogRepository:
    def __init__(self, session: Session):
        self.session = session

    def save(self, entry: AuditLog) -> AuditLog:
        self.session.add(entry)
        self.session.flush()
        self.session.commit()
        return entry

    def get_all(self, limit: int = 100, offset: int = 0) -> list[AuditLog]:
        return list(self.session.scalars(
            select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
        ).all())

    def get_by_user(self, user_id: int, limit: int = 100, offset: int = 0) -> list[AuditLog]:
        return list(self.session.scalars(
            select(AuditLog)
            .where(AuditLog.user_id == user_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit).offset(offset)
        ).all())

    def get_by_target(self, target_type: str, target_id: int) -> list[AuditLog]:
        return list(self.session.scalars(
            select(AuditLog)
            .where(AuditLog.target_type == target_type, AuditLog.target_id == target_id)
            .order_by(AuditLog.created_at.desc())
        ).all())
