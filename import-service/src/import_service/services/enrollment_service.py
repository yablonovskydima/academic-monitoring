from sqlalchemy.orm import Session

from import_service.models.enrollment import Enrollment
from import_service.repositories.enrollment_repository import EnrollmentRepository
from import_service.schemas.enrollment import EnrollmentCreate, EnrollmentUpdate


class EnrollmentService:
    def __init__(self, db: Session):
        self.repo = EnrollmentRepository(db)

    def get_by_id(self, enrollment_id: int) -> Enrollment | None:
        return self.repo.get_by_id(enrollment_id)

    def get_by_student(self, student_id: int) -> list[Enrollment]:
        return self.repo.get_by_student(student_id)

    def get_by_offering(self, subject_offering_id: int) -> list[Enrollment]:
        return self.repo.get_by_offering(subject_offering_id)

    def create(self, data: EnrollmentCreate) -> Enrollment:
        enrollment = Enrollment(**data.model_dump())
        return self.repo.save(enrollment)

    def bulk_create(self, items_data: list[EnrollmentCreate]) -> None:
        enrollments = [Enrollment(**data.model_dump()) for data in items_data]
        self.repo.bulk_save(enrollments)

    def update(self, enrollment_id: int, data: EnrollmentUpdate) -> Enrollment | None:
        enrollment = self.repo.get_by_id(enrollment_id)
        if enrollment is None:
            return None

        update_fields = data.model_dump(exclude_unset=True)
        for key, value in update_fields.items():
            setattr(enrollment, key, value)

        return self.repo.save(enrollment)

    def delete(self, enrollment_id: int) -> bool:
        return self.repo.delete(enrollment_id)