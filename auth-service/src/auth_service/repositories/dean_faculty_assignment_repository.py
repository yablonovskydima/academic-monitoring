from sqlalchemy import select
from sqlalchemy.orm import Session

from auth_service.models.dean_faculty_assignment import DeanFacultyAssignment


class DeanFacultyAssignmentRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, assignment_id: int) -> DeanFacultyAssignment | None:
        return self.session.get(DeanFacultyAssignment, assignment_id)

    def get_by_user(self, user_id: int) -> list[DeanFacultyAssignment]:
        return list(self.session.scalars(
            select(DeanFacultyAssignment).where(DeanFacultyAssignment.user_id == user_id)
        ).all())

    def exists(self, user_id: int, faculty_id: int) -> bool:
        return self.session.scalars(
            select(DeanFacultyAssignment).where(
                DeanFacultyAssignment.user_id == user_id,
                DeanFacultyAssignment.faculty_id == faculty_id,
            )
        ).first() is not None

    def save(self, assignment: DeanFacultyAssignment) -> DeanFacultyAssignment:
        self.session.add(assignment)
        self.session.flush()
        self.session.commit()
        return assignment

    def delete(self, assignment_id: int) -> bool:
        assignment = self.session.get(DeanFacultyAssignment, assignment_id)
        if assignment is None:
            return False
        self.session.delete(assignment)
        self.session.commit()
        return True
