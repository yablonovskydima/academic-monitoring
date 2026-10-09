import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Boolean, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from auth_service.database import Base

if TYPE_CHECKING:
    from auth_service.models.refresh_token import RefreshToken
    from auth_service.models.curator_group_assignment import CuratorGroupAssignment
    from auth_service.models.dean_faculty_assignment import DeanFacultyAssignment


class UserRoleEnum(str, enum.Enum):
    admin = "admin"
    dean = "dean"
    curator = "curator"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    login: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRoleEnum] = mapped_column(SAEnum(UserRoleEnum, name="user_role_enum"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="user")
    curator_group_assignments: Mapped[list["CuratorGroupAssignment"]] = relationship(back_populates="curator")
    dean_faculty_assignments: Mapped[list["DeanFacultyAssignment"]] = relationship(back_populates="dean")
