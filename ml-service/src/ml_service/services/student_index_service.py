from sqlalchemy.orm import Session

from ml_service.models.student_index import StudentIndex
from ml_service.repositories.student_index_repository import StudentIndexRepository
from ml_service.schemas.student_index import StudentIndexCreate


class StudentIndexService:
    def __init__(self, db: Session):
        self.repo = StudentIndexRepository(db)

    def get_by_id(self, index_id: int) -> StudentIndex | None:
        return self.repo.get_by_id(index_id)

    def get_latest_for_student(self, student_id: int) -> StudentIndex | None:
        return self.repo.get_latest_by_student(student_id)

    def get_latest_for_student_full(self, student_id: int) -> StudentIndex | None:
        return self.repo.get_latest_by_student_full(student_id)

    def get_history_for_student(self, student_id: int) -> list[StudentIndex]:
        return self.repo.get_history_by_student(student_id)

    def create(self, data: StudentIndexCreate) -> StudentIndex:
        student_index = StudentIndex(**data.model_dump())
        return self.repo.save(student_index)

    def bulk_create(self, items_data: list[StudentIndexCreate]) -> list[StudentIndex]:
        indexes = [StudentIndex(**data.model_dump()) for data in items_data]
        return self.repo.bulk_save(indexes)

    def delete(self, index_id: int) -> bool:
        return self.repo.delete(index_id)