from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth_service.database import get_db
from auth_service.dependencies import get_current_user
from auth_service.models.user import User
from auth_service.schemas.curator_group_assignment import AssignGroupRequest, CuratorGroupAssignmentOut
from auth_service.services.curator_group_assignment_service import CuratorGroupAssignmentService

router = APIRouter(prefix="/curator-assignments", tags=["curator_assignments"])


@router.post("/", response_model=CuratorGroupAssignmentOut, status_code=status.HTTP_201_CREATED)
def assign_self_to_group(
    data: AssignGroupRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return CuratorGroupAssignmentService(db).assign_self(current_user.id, data.group_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/me", response_model=list[int])
def get_my_groups(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return CuratorGroupAssignmentService(db).get_group_ids_for_user(current_user.id)


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_assignment(
    assignment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = CuratorGroupAssignmentService(db)
    assignment = service.get_by_id(assignment_id)
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

    if assignment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your assignment")

    service.remove(assignment_id)
