from sqlalchemy import select
from sqlalchemy.orm import Session

from auth_service.models.curator_group_assignment import CuratorGroupAssignment


class CuratorGroupAssignmentRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, assignment_id: int) -> CuratorGroupAssignment | None:
        return self.session.get(CuratorGroupAssignment, assignment_id)

    def get_by_user(self, user_id: int) -> list[CuratorGroupAssignment]:
        return list(self.session.scalars(
            select(CuratorGroupAssignment).where(CuratorGroupAssignment.user_id == user_id)
        ).all())

    def exists(self, user_id: int, group_id: int) -> bool:
        return self.session.scalars(
            select(CuratorGroupAssignment).where(
                CuratorGroupAssignment.user_id == user_id,
                CuratorGroupAssignment.group_id == group_id,
            )
        ).first() is not None

    def save(self, assignment: CuratorGroupAssignment) -> CuratorGroupAssignment:
        self.session.add(assignment)
        self.session.flush()
        self.session.commit()
        return assignment

    def delete(self, assignment_id: int) -> bool:
        assignment = self.session.get(CuratorGroupAssignment, assignment_id)
        if assignment is None:
            return False
        self.session.delete(assignment)
        self.session.commit()
        return True
