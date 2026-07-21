from sqlalchemy.orm import Session

from import_service.models.student import Student
from import_service.repositories.student_repository import StudentRepository
from import_service.schemas.student import StudentCreate, StudentUpdate


class StudentService:
    def __init__(self, db: Session):
        self.repo = StudentRepository(db)

    def get_all(self) -> list[Student]:
        return self.repo.get_all()

    def get_by_id(self, student_id: int) -> Student | None:
        return self.repo.get_by_id(student_id)

    def get_by_group(self, group_id: int) -> list[Student]:
        return self.repo.get_by_group(group_id)

    def get_full(self, student_id: int) -> Student | None:
        return self.repo.get_full_by_id(student_id)

    def create(self, data: StudentCreate) -> Student:
        student = Student(**data.model_dump())
        return self.repo.save(student)

    def bulk_create(self, items_data: list[StudentCreate]) -> None:
        students = [Student(**data.model_dump()) for data in items_data]
        self.repo.bulk_save(students)

    def update(self, student_id: int, data: StudentUpdate) -> Student | None:
        student = self.repo.get_by_id(student_id)
        if student is None:
            return None

        update_fields = data.model_dump(exclude_unset=True)
        for key, value in update_fields.items():
            setattr(student, key, value)

        return self.repo.save(student)

    def delete(self, student_id: int) -> bool:
        return self.repo.delete(student_id)