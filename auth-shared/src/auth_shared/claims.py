import enum

import jwt
from pydantic import BaseModel

from auth_shared.config import JWT_ALGORITHM, JWT_SECRET_KEY


class Role(str, enum.Enum):
    admin = "admin"
    dean = "dean"
    curator = "curator"


class Claims(BaseModel):
    user_id: int
    role: Role
    group_ids: list[int] = []
    faculty_ids: list[int] = []


class InvalidTokenError(Exception):
    pass


def decode_and_verify(token: str) -> Claims:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as e:
        raise InvalidTokenError(str(e)) from e

    if payload.get("type") != "access":
        raise InvalidTokenError("Not an access token")

    try:
        return Claims(
            user_id=int(payload["sub"]),
            role=payload["role"],
            group_ids=payload.get("group_ids", []),
            faculty_ids=payload.get("faculty_ids", []),
        )
    except (KeyError, ValueError) as e:
        raise InvalidTokenError(f"Malformed token payload: {e}") from e
