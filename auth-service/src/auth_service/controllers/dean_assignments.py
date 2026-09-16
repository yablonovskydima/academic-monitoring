from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth_service.database import get_db
from auth_service.dependencies import get_current_user
from auth_service.models.user import User
from auth_service.schemas.dean_faculty_assignment import AssignDeanRequest, DeanFacultyAssignmentOut
from auth_service.services.dean_faculty_assignment_service import DeanFacultyAssignmentService

router = APIRouter(prefix="/dean-assignments", tags=["dean_assignments"])


@router.post("/", response_model=DeanFacultyAssignmentOut, status_code=status.HTTP_201_CREATED)
def assign_dean_to_faculty(
    data: AssignDeanRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # TODO(RBAC): admin-only once role-based route gating exists.
    try:
        return DeanFacultyAssignmentService(db).assign(current_user.id, data.dean_user_id, data.faculty_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{user_id}", response_model=list[int])
def get_faculties_for_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return DeanFacultyAssignmentService(db).get_faculty_ids_for_user(user_id)


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_assignment(
    assignment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # TODO(RBAC): admin-only once role-based route gating exists.
    service = DeanFacultyAssignmentService(db)
    assignment = service.get_by_id(assignment_id)
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

    service.remove(assignment_id)
