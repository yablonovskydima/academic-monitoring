from sqlalchemy.orm import Session

from import_service.models.class_session import ClassSession
from import_service.repositories.class_session_repository import ClassSessionRepository
from import_service.schemas.class_session import ClassSessionCreate, ClassSessionUpdate


class ClassSessionService:
    def __init__(self, db: Session):
        self.repo = ClassSessionRepository(db)

    def get_by_id(self, session_id: int) -> ClassSession | None:
        return self.repo.get_by_id(session_id)

    def get_by_offering(self, subject_offering_id: int) -> list[ClassSession]:
        return self.repo.get_by_offering(subject_offering_id)

    def get_full(self, session_id: int) -> ClassSession | None:
        return self.repo.get_full_by_id(session_id)

    def create(self, data: ClassSessionCreate) -> ClassSession:
        class_session = ClassSession(**data.model_dump())
        return self.repo.save(class_session)

    def bulk_create(self, items_data: list[ClassSessionCreate]) -> list[ClassSession]:
        class_sessions = [ClassSession(**data.model_dump()) for data in items_data]
        return self.repo.bulk_save(class_sessions)

    def update(self, session_id: int, data: ClassSessionUpdate) -> ClassSession | None:
        class_session = self.repo.get_by_id(session_id)
        if class_session is None:
            return None

        update_fields = data.model_dump(exclude_unset=True)
        for key, value in update_fields.items():
            setattr(class_session, key, value)

        return self.repo.save(class_session)

    def delete(self, session_id: int) -> bool:
        return self.repo.delete(session_id)