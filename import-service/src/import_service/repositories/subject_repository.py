from sqlalchemy import select
from sqlalchemy.orm import Session

from import_service.models.subject import Subject


class SubjectRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_all(self) -> list[Subject]:
         return list(self.session.scalars(select(Subject)).all())

    def get_by_id(self, subject_id: int) -> Subject | None:
        return self.session.scalars(
            select(Subject).where(Subject.id == subject_id)
        ).first()

    def save(self, subject: Subject) -> Subject:
        self.session.add(subject)
        self.session.commit()
        self.session.refresh(subject)
        return subject

    def bulk_save(self, subjects: list[Subject]) -> list[Subject]:
        self.session.add_all(subjects)
        self.session.flush()
        self.session.commit()
        return subjects

    def delete(self, subject_id: int) -> bool:
        subject = self.get_by_id(subject_id)
        if subject is None:
            return False
        self.session.delete(subject)
        self.session.commit()
        return True