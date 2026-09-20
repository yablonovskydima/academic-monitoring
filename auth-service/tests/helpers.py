from auth_service.models.user import User, UserRoleEnum
from auth_service.schemas.user import UserCreate
from auth_service.services.user_service import UserService

PASSWORD = "Str0ng!Pass1"


def make_user(db_session, role: UserRoleEnum, email: str) -> User:
    return UserService(db_session).create(UserCreate(
        first_name="Test",
        last_name="User",
        email=email,
        password=PASSWORD,
        role=role,
    ))


def login(client, email: str, password: str = PASSWORD) -> dict:
    response = client.post("/auth/login", json={
        "login": email.split("@")[0],
        "password": password,
    })
    assert response.status_code == 200, response.text
    return response.json()


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
