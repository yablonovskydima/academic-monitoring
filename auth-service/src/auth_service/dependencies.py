from auth_shared import Claims, get_claims
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth_service.database import get_db
from auth_service.models.user import User, UserRoleEnum
from auth_service.services.user_service import UserService

_INVALID_TOKEN = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid or expired token",
    headers={"WWW-Authenticate": "Bearer"},
)
_FORBIDDEN = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="You do not have permission to perform this action",
)


def get_current_user(
    claims: Claims = Depends(get_claims),
    db: Session = Depends(get_db),
) -> User:
    user = UserService(db).get_by_id(claims.user_id)
    if user is None or not user.is_active:
        raise _INVALID_TOKEN

    return user


def require_role(*roles: UserRoleEnum):
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise _FORBIDDEN
        return current_user

    return dependency
