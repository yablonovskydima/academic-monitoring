from sqlalchemy import select
from sqlalchemy.orm import Session

from auth_service.models.user import User


class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, user_id: int) -> User | None:
        return self.session.scalars(
            select(User).where(User.id == user_id)
        ).first()

    def get_by_email(self, email: str) -> User | None:
        return self.session.scalars(
            select(User).where(User.email == email)
        ).first()

    def get_by_login(self, login: str) -> User | None:
        return self.session.scalars(
            select(User).where(User.login == login)
        ).first()

    def get_all(self) -> list[User]:
        return list(self.session.scalars(select(User)).all())

    def save(self, user: User) -> User:
        self.session.add(user)
        self.session.flush()
        self.session.commit()
        return user

    def delete(self, user_id: int) -> bool:
        user = self.get_by_id(user_id)
        if user is None:
            return False
        self.session.delete(user)
        self.session.commit()
        return True
