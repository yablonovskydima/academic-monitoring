from sqlalchemy.orm import Session

from import_service.models.semester import Semester
from import_service.repositories.semester_repository import SemesterRepository
from import_service.schemas.semester import SemesterCreate, SemesterUpdate


class SemesterService:
    def __init__(self, db: Session):
        self.repo = SemesterRepository(db)

    def get_all(self) -> list[Semester]:
        return self.repo.get_all()

    def get_by_id(self, semester_id: int) -> Semester | None:
        return self.repo.get_by_id(semester_id)

    def get_current(self) -> Semester | None:
        return self.repo.get_current()

    def create(self, data: SemesterCreate) -> Semester:
        semester = Semester(**data.model_dump())
        return self.repo.save(semester)

    def bulk_create(self, items_data: list[SemesterCreate]) -> None:
        semesters = [Semester(**data.model_dump()) for data in items_data]
        self.repo.bulk_save(semesters)

    def update(self, semester_id: int, data: SemesterUpdate) -> Semester | None:
        semester = self.repo.get_by_id(semester_id)
        if semester is None:
            return None

        update_fields = data.model_dump(exclude_unset=True)
        for key, value in update_fields.items():
            setattr(semester, key, value)

        return self.repo.save(semester)

    def delete(self, semester_id: int) -> bool:
        return self.repo.delete(semester_id)