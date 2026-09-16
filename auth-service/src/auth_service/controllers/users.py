from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth_service.database import get_db
from auth_service.dependencies import get_current_user
from auth_service.models.user import User
from auth_service.schemas.user import UserOut
from auth_service.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])

# TODO(RBAC): both endpoints below must be admin-only once role-based

@router.post("/{user_id}/activate", response_model=UserOut)
def activate_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = UserService(db).set_active(current_user.id, user_id, True)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.post("/{user_id}/deactivate", response_model=UserOut)
def deactivate_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = UserService(db).set_active(current_user.id, user_id, False)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user
