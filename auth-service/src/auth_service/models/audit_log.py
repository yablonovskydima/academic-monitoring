from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from auth_service.database import Base

if TYPE_CHECKING:
    from auth_service.models.user import User


class AuditLog(Base):
    """
    AGENT NOTE: this table is the accountability trail for the whole
    platform (see CLAUDE.md — "who changed a threshold", "who viewed
    a student's risk data", "who triggered a retrain"). It only has
    value if every service that performs a sensitive action actually
    writes to it. When you add or change business logic — here or in
    another service — that reads sensitive student data, or changes
    something another user relies on (thresholds, permissions, model
    activation), add or update the corresponding audit log write. Do
    not treat this table as auth-service-only bookkeeping.
    """

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    target_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    target_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)

    user: Mapped["User"] = relationship()
