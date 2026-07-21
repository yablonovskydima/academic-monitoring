from sqlalchemy.orm import Session

from import_service.models.grade import Grade
from import_service.repositories.grade_repository import GradeRepository
from import_service.schemas.grade import GradeCreate, GradeUpdate


class GradeService:
    def __init__(self, db: Session):
        self.repo = GradeRepository(db)

    def get_by_id(self, grade_id: int) -> Grade | None:
        return self.repo.get_by_id(grade_id)

    def get_by_student(self, student_id: int) -> list[Grade]:
        return self.repo.get_by_student(student_id)

    def get_by_session(self, class_session_id: int) -> list[Grade]:
        return self.repo.get_by_session(class_session_id)

    def create(self, data: GradeCreate) -> Grade:
        grade = Grade(**data.model_dump())
        return self.repo.save(grade)

    def bulk_create(self, items_data: list[GradeCreate]) -> None:
        grades = [Grade(**data.model_dump()) for data in items_data]
        self.repo.bulk_save(grades)

    def update(self, grade_id: int, data: GradeUpdate) -> Grade | None:
        grade = self.repo.get_by_id(grade_id)
        if grade is None:
            return None

        update_fields = data.model_dump(exclude_unset=True)
        for key, value in update_fields.items():
            setattr(grade, key, value)

        return self.repo.save(grade)

    def delete(self, grade_id: int) -> bool:
        return self.repo.delete(grade_id)