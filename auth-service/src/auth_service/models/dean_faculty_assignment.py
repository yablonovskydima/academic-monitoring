from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from auth_service.database import Base

if TYPE_CHECKING:
    from auth_service.models.user import User


class DeanFacultyAssignment(Base):
    __tablename__ = "dean_faculty_assignments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    faculty_id: Mapped[int] = mapped_column(Integer, index=True)
    assigned_at: Mapped[datetime] = mapped_column(server_default=func.now())

    dean: Mapped["User"] = relationship(back_populates="dean_faculty_assignments")
