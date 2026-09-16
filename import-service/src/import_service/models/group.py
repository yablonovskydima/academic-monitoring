from typing import TYPE_CHECKING

from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from import_service.database import Base
from import_service.models.student import Student

if TYPE_CHECKING:
    from import_service.models.faculty import Faculty


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50))
    faculty_id: Mapped[int] = mapped_column(ForeignKey("faculties.id"))
    course_year: Mapped[int] = mapped_column(Integer)

    faculty: Mapped["Faculty"] = relationship(back_populates="groups")
    students: Mapped[list["Student"]] = relationship(back_populates="group")
