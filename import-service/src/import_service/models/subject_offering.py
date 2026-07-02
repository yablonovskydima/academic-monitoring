from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from import_service.database import Base

if TYPE_CHECKING:
    from import_service.models.class_session import ClassSession
    from import_service.models.enrollment import Enrollment
    from import_service.models.semester import Semester
    from import_service.models.subject import Subject
    from import_service.models.teacher import Teacher


class SubjectOffering(Base):
    __tablename__ = "subject_offerings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"))
    semester_id: Mapped[int] = mapped_column(ForeignKey("semesters.id"))
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id"))
    max_practice_score: Mapped[int] = mapped_column(Integer, default=50)
    max_exam_score: Mapped[int] = mapped_column(Integer, default=50)

    subject: Mapped["Subject"] = relationship(back_populates="subject_offerings")
    semester: Mapped["Semester"] = relationship(back_populates="subject_offerings")
    teacher: Mapped["Teacher"] = relationship(back_populates="subject_offerings")
    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="subject_offering")
    class_sessions: Mapped[list["ClassSession"]] = relationship(back_populates="subject_offering")