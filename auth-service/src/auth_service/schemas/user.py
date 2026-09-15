from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from auth_service.models.user import UserRoleEnum
from auth_service.validators import validate_name, validate_password_strength


class UserCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    role: UserRoleEnum

    @field_validator("first_name", "last_name")
    @classmethod
    def _validate_names(cls, v: str) -> str:
        return validate_name(v)

    @field_validator("password")
    @classmethod
    def _validate_password(cls, v: str) -> str:
        return validate_password_strength(v)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str
    last_name: str
    email: str
    login: str
    role: UserRoleEnum
    is_active: bool
    created_at: datetime
    updated_at: datetime
