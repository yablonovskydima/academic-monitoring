from sqlalchemy.orm import Session

from auth_service.clients.import_service_client import ImportServiceClient
from auth_service.models.dean_faculty_assignment import DeanFacultyAssignment
from auth_service.models.user import UserRoleEnum
from auth_service.repositories.dean_faculty_assignment_repository import DeanFacultyAssignmentRepository
from auth_service.schemas.audit_log import AuditLogCreate
from auth_service.services.audit_log_service import AuditLogService
from auth_service.services.user_service import UserService


class DeanFacultyAssignmentService:

    def __init__(self, db: Session, import_client: ImportServiceClient | None = None):
        self.repo = DeanFacultyAssignmentRepository(db)
        self.user_service = UserService(db)
        self.audit_log_service = AuditLogService(db)
        self.import_client = import_client or ImportServiceClient()

    def get_by_id(self, assignment_id: int) -> DeanFacultyAssignment | None:
        return self.repo.get_by_id(assignment_id)

    def get_faculty_ids_for_user(self, user_id: int) -> list[int]:
        return [a.faculty_id for a in self.repo.get_by_user(user_id)]

    def assign(self, admin_user_id: int, dean_user_id: int, faculty_id: int) -> DeanFacultyAssignment:
        if not self.user_service.has_role(dean_user_id, UserRoleEnum.dean):
            raise ValueError(f"User {dean_user_id} does not have the dean role")

        if self.import_client.get_faculty(faculty_id) is None:
            raise ValueError(f"Faculty {faculty_id} does not exist in import-service")

        if self.repo.exists(dean_user_id, faculty_id):
            raise ValueError(f"User {dean_user_id} is already assigned to faculty {faculty_id}")

        assignment = self.repo.save(DeanFacultyAssignment(user_id=dean_user_id, faculty_id=faculty_id))

        self.audit_log_service.log(AuditLogCreate(
            user_id=admin_user_id,
            action="dean_faculty_assignment_created",
            target_type="faculty",
            target_id=faculty_id,
            details={"dean_user_id": dean_user_id},
        ))

        return assignment

    def remove(self, assignment_id: int) -> bool:
        return self.repo.delete(assignment_id)
