from sqlalchemy.orm import Session

from auth_service.models.user import User, UserRoleEnum
from auth_service.repositories.user_repository import UserRepository
from auth_service.schemas.user import UserCreate
from auth_service.security import hash_password, verify_password
from auth_service.validators import validate_login


class UserService:
    def __init__(self, db: Session):
        self.repo = UserRepository(db)

    def get_by_id(self, user_id: int) -> User | None:
        return self.repo.get_by_id(user_id)

    def get_by_email(self, email: str) -> User | None:
        return self.repo.get_by_email(email)

    def get_all(self) -> list[User]:
        return self.repo.get_all()

    def has_role(self, user_id: int, role: UserRoleEnum) -> bool:
        user = self.repo.get_by_id(user_id)
        return user is not None and user.role == role

    def create(self, data: UserCreate) -> User:
        login = data.email.split("@")[0]
        if self.repo.get_by_login(login) is not None:
            raise ValueError(f"Login {login!r} (derived from email) is already taken")

        user = User(
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            login=login,
            hashed_password=hash_password(data.password),
            role=data.role,
        )
        return self.repo.save(user)

    def authenticate(self, login: str, password: str) -> User | None:
        user = self.repo.get_by_login(login)
        if user is None or not user.is_active:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    def delete(self, user_id: int) -> bool:
        return self.repo.delete(user_id)
