from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from import_service.database import Base

if TYPE_CHECKING:
    from import_service.models.class_session import ClassSession
    from import_service.models.student import Student


class Attendance(Base):
    __tablename__ = "attendance"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    class_session_id: Mapped[int] = mapped_column(ForeignKey("class_sessions.id"), index=True)
    is_absent: Mapped[bool] = mapped_column(Boolean, default=False)
    is_worked_off: Mapped[bool] = mapped_column(Boolean, default=False)
    is_excused: Mapped[bool] = mapped_column(Boolean, default=False)

    student: Mapped["Student"] = relationship(back_populates="attendances")
    class_session: Mapped["ClassSession"] = relationship(back_populates="attendances")