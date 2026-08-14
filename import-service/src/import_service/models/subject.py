from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from import_service.database import Base
from import_service.models.subject_offering import SubjectOffering


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200))
    is_elective: Mapped[bool] = mapped_column(Boolean, default=True)

    subject_offerings: Mapped[list["SubjectOffering"]] = relationship(back_populates="subject")