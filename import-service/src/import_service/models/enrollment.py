from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from import_service.database import Base
from import_service.models.student import Student
from import_service.models.subject_offering import SubjectOffering


class Enrollment(Base):
    __tablename__ = "enrollments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    subject_offering_id: Mapped[int] = mapped_column(ForeignKey("subject_offerings.id"), index=True)
    enrolled_at: Mapped[datetime] = mapped_column(server_default=func.now())

    student: Mapped["Student"] = relationship(back_populates="enrollments")
    subject_offering: Mapped["SubjectOffering"] = relationship(back_populates="enrollments")