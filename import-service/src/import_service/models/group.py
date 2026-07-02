from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from import_service.database import Base
from import_service.models.student import Student


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50))
    faculty: Mapped[str] = mapped_column(String(100))
    course_year: Mapped[int] = mapped_column(Integer)

    students: Mapped[list["Student"]] = relationship(back_populates="group")