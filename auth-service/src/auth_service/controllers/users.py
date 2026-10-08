from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth_service.database import get_db
from auth_service.dependencies import require_role
from auth_service.models.user import User, UserRoleEnum
from auth_service.schemas.user import AdminUserCreate, ChangeRoleRequest, UserOut, UserUpdate
from auth_service.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    data: AdminUserCreate,
    current_user: User = Depends(require_role(UserRoleEnum.admin)),
    db: Session = Depends(get_db),
):
    try:
        return UserService(db).create_as_admin(current_user.id, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    data: UserUpdate,
    current_user: User = Depends(require_role(UserRoleEnum.admin)),
    db: Session = Depends(get_db),
):
    try:
        user = UserService(db).update_profile(current_user.id, user_id, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.post("/{user_id}/activate", response_model=UserOut)
def activate_user(
    user_id: int,
    current_user: User = Depends(require_role(UserRoleEnum.admin)),
    db: Session = Depends(get_db),
):
    try:
        user = UserService(db).set_active(current_user.id, user_id, True)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.post("/{user_id}/deactivate", response_model=UserOut)
def deactivate_user(
    user_id: int,
    current_user: User = Depends(require_role(UserRoleEnum.admin)),
    db: Session = Depends(get_db),
):
    try:
        user = UserService(db).set_active(current_user.id, user_id, False)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.post("/{user_id}/role", response_model=UserOut)
def change_user_role(
    user_id: int,
    data: ChangeRoleRequest,
    current_user: User = Depends(require_role(UserRoleEnum.admin)),
    db: Session = Depends(get_db),
):
    try:
        user = UserService(db).set_role(current_user.id, user_id, data.role)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user
