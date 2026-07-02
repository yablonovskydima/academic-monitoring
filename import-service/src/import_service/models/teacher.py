from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from import_service.database import Base
from import_service.models.subject_offering import SubjectOffering


class Teacher(Base):
    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(200))
    department: Mapped[str] = mapped_column(String(150))

    subject_offerings: Mapped[list["SubjectOffering"]] = relationship(back_populates="teacher")