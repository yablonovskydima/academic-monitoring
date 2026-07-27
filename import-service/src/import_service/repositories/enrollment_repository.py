from sqlalchemy import select
from sqlalchemy.orm import Session

from import_service.models.enrollment import Enrollment


class EnrollmentRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, enrollment_id: int) -> Enrollment | None:
        return self.session.scalars(
            select(Enrollment).where(Enrollment.id == enrollment_id)
        ).first()

    def get_by_student(self, student_id: int) -> list[Enrollment]:
        return list(self.session.scalars(
            select(Enrollment).where(Enrollment.student_id == student_id)
        ).all())

    def get_by_offering(self, subject_offering_id: int) -> list[Enrollment]:
        return list(self.session.scalars(
            select(Enrollment).where(Enrollment.subject_offering_id == subject_offering_id)
        ).all())

    def save(self, enrollment: Enrollment) -> Enrollment:
        self.session.add(enrollment)
        self.session.commit()
        self.session.refresh(enrollment)
        return enrollment

    def bulk_save(self, enrollments: list[Enrollment]) -> list[Enrollment]:
        self.session.add_all(enrollments)
        self.session.flush()
        self.session.commit()
        return enrollments

    def delete(self, enrollment_id: int) -> bool:
        enrollment = self.get_by_id(enrollment_id)
        if enrollment is None:
            return False
        self.session.delete(enrollment)
        self.session.commit()
        return True