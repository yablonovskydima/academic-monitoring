from sqlalchemy.orm import Session

from import_service.models.faculty import Faculty
from import_service.repositories.faculty_repository import FacultyRepository
from import_service.schemas.faculty import FacultyCreate, FacultyUpdate


class FacultyService:
    def __init__(self, db: Session):
        self.repo = FacultyRepository(db)

    def get_all(self) -> list[Faculty]:
        return self.repo.get_all()

    def get_by_id(self, faculty_id: int) -> Faculty | None:
        return self.repo.get_by_id(faculty_id)

    def get_full(self, faculty_id: int) -> Faculty | None:
        return self.repo.get_full_by_id(faculty_id)

    def create(self, data: FacultyCreate) -> Faculty:
        faculty = Faculty(**data.model_dump())
        return self.repo.save(faculty)

    def bulk_create(self, items_data: list[FacultyCreate]) -> list[Faculty]:
        faculties = [Faculty(**data.model_dump()) for data in items_data]
        return self.repo.bulk_save(faculties)

    def update(self, faculty_id: int, data: FacultyUpdate) -> Faculty | None:
        faculty = self.repo.get_by_id(faculty_id)
        if faculty is None:
            return None

        update_fields = data.model_dump(exclude_unset=True)
        for key, value in update_fields.items():
            setattr(faculty, key, value)

        return self.repo.save(faculty)

    def delete(self, faculty_id: int) -> bool:
        return self.repo.delete(faculty_id)
