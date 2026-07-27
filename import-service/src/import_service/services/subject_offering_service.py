from sqlalchemy.orm import Session

from import_service.models.subject_offering import SubjectOffering
from import_service.repositories.subject_offering_repository import SubjectOfferingRepository
from import_service.schemas.subject_offering import SubjectOfferingCreate, SubjectOfferingUpdate


class SubjectOfferingService:
    def __init__(self, db: Session):
        self.repo = SubjectOfferingRepository(db)

    def get_all(self) -> list[SubjectOffering]:
        return self.repo.get_all()

    def get_by_id(self, offering_id: int) -> SubjectOffering | None:
        return self.repo.get_by_id(offering_id)

    def get_by_semester(self, semester_id: int) -> list[SubjectOffering]:
        return self.repo.get_by_semester(semester_id)

    def get_full(self, offering_id: int) -> SubjectOffering | None:
        return self.repo.get_full_by_id(offering_id)

    def create(self, data: SubjectOfferingCreate) -> SubjectOffering:
        offering = SubjectOffering(**data.model_dump())
        return self.repo.save(offering)

    def bulk_create(self, items_data: list[SubjectOfferingCreate]) -> list[SubjectOffering]:
        offerings = [SubjectOffering(**data.model_dump()) for data in items_data]
        return self.repo.bulk_save(offerings)

    def update(self, offering_id: int, data: SubjectOfferingUpdate) -> SubjectOffering | None:
        offering = self.repo.get_by_id(offering_id)
        if offering is None:
            return None

        update_fields = data.model_dump(exclude_unset=True)
        for key, value in update_fields.items():
            setattr(offering, key, value)

        return self.repo.save(offering)

    def delete(self, offering_id: int) -> bool:
        return self.repo.delete(offering_id)