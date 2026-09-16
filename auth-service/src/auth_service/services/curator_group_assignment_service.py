from sqlalchemy.orm import Session

from auth_service.clients.import_service_client import ImportServiceClient
from auth_service.models.curator_group_assignment import CuratorGroupAssignment
from auth_service.models.user import UserRoleEnum
from auth_service.repositories.curator_group_assignment_repository import CuratorGroupAssignmentRepository
from auth_service.schemas.audit_log import AuditLogCreate
from auth_service.services.audit_log_service import AuditLogService
from auth_service.services.user_service import UserService


class CuratorGroupAssignmentService:
    def __init__(self, db: Session, import_client: ImportServiceClient | None = None):
        self.repo = CuratorGroupAssignmentRepository(db)
        self.user_service = UserService(db)
        self.audit_log_service = AuditLogService(db)
        self.import_client = import_client or ImportServiceClient()

    def get_by_id(self, assignment_id: int) -> CuratorGroupAssignment | None:
        return self.repo.get_by_id(assignment_id)

    def get_group_ids_for_user(self, user_id: int) -> list[int]:
        return [a.group_id for a in self.repo.get_by_user(user_id)]

    def assign_self(self, user_id: int, group_id: int) -> CuratorGroupAssignment:
        if not self.user_service.has_role(user_id, UserRoleEnum.curator):
            raise ValueError(f"User {user_id} does not have the curator role")

        if self.import_client.get_group(group_id) is None:
            raise ValueError(f"Group {group_id} does not exist in import-service")

        if self.repo.exists(user_id, group_id):
            raise ValueError(f"User {user_id} is already assigned to group {group_id}")

        assignment = self.repo.save(CuratorGroupAssignment(user_id=user_id, group_id=group_id))

        self.audit_log_service.log(AuditLogCreate(
            user_id=user_id,
            action="curator_group_assignment_created",
            target_type="group",
            target_id=group_id,
        ))

        return assignment

    def remove(self, assignment_id: int) -> bool:
        return self.repo.delete(assignment_id)
