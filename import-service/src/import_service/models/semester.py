from datetime import date

from sqlalchemy import String, Integer, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship

from import_service.database import Base
from import_service.models.subject_offering import SubjectOffering


class Semester(Base):
    __tablename__ = "semesters"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    academic_year: Mapped[str] = mapped_column(String(9))  # "2025/2026"
    term: Mapped[int] = mapped_column(Integer)  # 1 або 2
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)

    subject_offerings: Mapped[list["SubjectOffering"]] = relationship(back_populates="semester")