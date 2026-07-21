from sqlalchemy.orm import Session

from import_service.models.teacher import Teacher
from import_service.repositories.teacher_repository import TeacherRepository
from import_service.schemas.teacher import TeacherCreate, TeacherUpdate


class TeacherService:
    def __init__(self, db: Session):
        self.repo = TeacherRepository(db)

    def get_all(self) -> list[Teacher]:
        return self.repo.get_all()

    def get_by_id(self, teacher_id: int) -> Teacher | None:
        return self.repo.get_by_id(teacher_id)

    def get_full(self, teacher_id: int) -> Teacher | None:
        return self.repo.get_full_by_id(teacher_id)

    def create(self, data: TeacherCreate) -> Teacher:
        teacher = Teacher(**data.model_dump())
        return self.repo.save(teacher)

    def bulk_create(self, items_data: list[TeacherCreate]) -> None:
        teachers = [Teacher(**data.model_dump()) for data in items_data]
        self.repo.bulk_save(teachers)

    def update(self, teacher_id: int, data: TeacherUpdate) -> Teacher | None:
        teacher = self.repo.get_by_id(teacher_id)
        if teacher is None:
            return None

        update_fields = data.model_dump(exclude_unset=True)
        for key, value in update_fields.items():
            setattr(teacher, key, value)

        return self.repo.save(teacher)

    def delete(self, teacher_id: int) -> bool:
        return self.repo.delete(teacher_id)