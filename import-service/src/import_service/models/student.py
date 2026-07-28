import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from import_service.database import Base

if TYPE_CHECKING:
    from import_service.models.attendance import Attendance
    from import_service.models.enrollment import Enrollment
    from import_service.models.grade import Grade
    from import_service.models.group import Group


class StudyMode(str, enum.Enum):
    full_time = "full_time"
    part_time = "part_time"
    individual_schedule = "individual_schedule"


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(200))
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), index=True)
    email: Mapped[str] = mapped_column(String(200), unique=True)
    study_mode: Mapped[StudyMode] = mapped_column(SAEnum(StudyMode, name="study_mode_enum"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    group: Mapped["Group"] = relationship(back_populates="students")
    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="student")
    attendances: Mapped[list["Attendance"]] = relationship(back_populates="student")
    grades: Mapped[list["Grade"]] = relationship(back_populates="student")