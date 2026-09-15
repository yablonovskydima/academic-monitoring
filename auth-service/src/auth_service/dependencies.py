from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from auth_service.database import get_db
from auth_service.models.user import User
from auth_service.security import InvalidTokenError, decode_access_token
from auth_service.services.user_service import UserService

_bearer_scheme = HTTPBearer()

_INVALID_TOKEN = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid or expired token",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:

    try:
        payload = decode_access_token(credentials.credentials)
    except InvalidTokenError:
        raise _INVALID_TOKEN

    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError):
        raise _INVALID_TOKEN

    user = UserService(db).get_by_id(user_id)
    if user is None or not user.is_active:
        raise _INVALID_TOKEN

    return user
