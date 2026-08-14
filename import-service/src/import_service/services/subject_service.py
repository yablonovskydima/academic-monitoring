from sqlalchemy.orm import Session

from import_service.models.subject import Subject
from import_service.repositories.subject_repository import SubjectRepository
from import_service.schemas.subject import SubjectCreate, SubjectUpdate


class SubjectService:
    def __init__(self, db: Session):
        self.repo = SubjectRepository(db)

    def get_all(self) -> list[Subject]:
        return self.repo.get_all()

    def get_by_id(self, subject_id: int) -> Subject | None:
        return self.repo.get_by_id(subject_id)

    def create(self, data: SubjectCreate) -> Subject:
        subject = Subject(**data.model_dump())
        return self.repo.save(subject)

    def bulk_create(self, items_data: list[SubjectCreate]) -> list[Subject]:
        subjects = [Subject(**data.model_dump()) for data in items_data]
        return self.repo.bulk_save(subjects)

    def update(self, subject_id: int, data: SubjectUpdate) -> Subject | None:
        subject = self.repo.get_by_id(subject_id)
        if subject is None:
            return None

        update_fields = data.model_dump(exclude_unset=True)
        for key, value in update_fields.items():
            setattr(subject, key, value)

        return self.repo.save(subject)

    def delete(self, subject_id: int) -> bool:
        return self.repo.delete(subject_id)