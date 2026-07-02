import enum
from datetime import date as date_type
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Date, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from import_service.database import Base

if TYPE_CHECKING:
    from import_service.models.attendance import Attendance
    from import_service.models.grade import Grade
    from import_service.models.subject_offering import SubjectOffering


class SessionType(str, enum.Enum):
    lecture = "lecture"
    lab = "lab"
    control = "control"
    exam = "exam"


class ClassSession(Base):
    __tablename__ = "class_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    subject_offering_id: Mapped[int] = mapped_column(ForeignKey("subject_offerings.id"))
    session_type: Mapped[SessionType] = mapped_column(SAEnum(SessionType, name="session_type_enum"))
    session_number: Mapped[int] = mapped_column(Integer)
    date: Mapped[date_type] = mapped_column(Date)

    subject_offering: Mapped["SubjectOffering"] = relationship(back_populates="class_sessions")
    attendances: Mapped[list["Attendance"]] = relationship(back_populates="class_session")
    grades: Mapped[list["Grade"]] = relationship(back_populates="class_session")