from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from import_service.database import Base

if TYPE_CHECKING:
    from import_service.models.group import Group


class Faculty(Base):
    __tablename__ = "faculties"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)

    groups: Mapped[list["Group"]] = relationship(back_populates="faculty")
