from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from insights_service.database import Base

if TYPE_CHECKING:
    from insights_service.models.group_summary import GroupSummary
    from insights_service.models.insight_change import InsightChange
    from insights_service.models.student_insight import StudentInsight


class InsightRun(Base):
    __tablename__ = "insight_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_job_id: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True)
    semester_id: Mapped[int] = mapped_column(Integer)
    students_count: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime]

    student_insights: Mapped[list["StudentInsight"]] = relationship(
        back_populates="run", cascade="all, delete-orphan",
    )
    changes: Mapped[list["InsightChange"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", foreign_keys="InsightChange.run_id",
    )
    group_summaries: Mapped[list["GroupSummary"]] = relationship(
        back_populates="run", cascade="all, delete-orphan",
    )
