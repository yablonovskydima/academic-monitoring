from pydantic import BaseModel, EmailStr, field_validator, model_validator

from auth_service.validators import validate_login, validate_name, validate_password_strength


class UserRegister(BaseModel):
 
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    confirm_password: str

    @field_validator("first_name", "last_name")
    @classmethod
    def _validate_names(cls, v: str) -> str:
        return validate_name(v)

    @field_validator("password")
    @classmethod
    def _validate_password(cls, v: str) -> str:
        return validate_password_strength(v)

    @model_validator(mode="after")
    def _passwords_must_match(self) -> "UserRegister":
        if self.password != self.confirm_password:
            raise ValueError("password and confirm_password do not match")
        return self


class LoginRequest(BaseModel):
    login: str
    password: str

    @field_validator("login")
    @classmethod
    def _validate_login(cls, v: str) -> str:
        return validate_login(v)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str
