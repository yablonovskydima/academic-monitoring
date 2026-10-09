from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator, model_validator

from auth_service.config import ALLOWED_EMAIL_DOMAINS
from auth_service.models.user import UserRoleEnum
from auth_service.utils.validators import validate_email_domain, validate_name, validate_password_strength


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


class ChangeRoleRequest(BaseModel):
    role: UserRoleEnum


class AdminUserCreate(UserCreate):
    @field_validator("email")
    @classmethod
    def _validate_email_domain(cls, v: str) -> str:
        return validate_email_domain(v, ALLOWED_EMAIL_DOMAINS)


class UserUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None

    @field_validator("first_name", "last_name")
    @classmethod
    def _validate_names(cls, v: str | None) -> str | None:
        return None if v is None else validate_name(v)

    @field_validator("email")
    @classmethod
    def _validate_email_domain(cls, v: str | None) -> str | None:
        return None if v is None else validate_email_domain(v, ALLOWED_EMAIL_DOMAINS)

    @model_validator(mode="after")
    def _at_least_one_field(self) -> "UserUpdate":
        if self.first_name is None and self.last_name is None and self.email is None:
            raise ValueError("provide at least one of first_name, last_name, email")
        return self
