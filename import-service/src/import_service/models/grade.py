from datetime import datetime

from sqlalchemy import ForeignKey, Numeric, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from import_service.database import Base
from import_service.models.class_session import ClassSession
from import_service.models.student import Student


class Grade(Base):
    __tablename__ = "grades"
    __table_args__ = (
        CheckConstraint("score >= 0 AND score <= 100", name="check_score_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"))
    class_session_id: Mapped[int] = mapped_column(ForeignKey("class_sessions.id"))
    score: Mapped[float] = mapped_column(Numeric(5, 2))
    deadline_at: Mapped[datetime | None] = mapped_column(nullable=True)
    graded_at: Mapped[datetime | None] = mapped_column(nullable=True)

    student: Mapped["Student"] = relationship(back_populates="grades")
    class_session: Mapped["ClassSession"] = relationship(back_populates="grades")