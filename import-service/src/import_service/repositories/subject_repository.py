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

    def create(self, subject: Subject) -> Subject:
        self.session.add(subject)
        self.session.commit()
        self.session.refresh(subject)
        return subject

    def bulk_create(self, subjects: list[Subject]) -> None:
        self.session.add_all(subjects)
        self.session.commit()

    def update(self, subject_id: int, **fields) -> Subject | None:  # todo dto for update
        subject = self.get_by_id(subject_id)
        if subject is None:
            return None
        for key, value in fields.items():
            setattr(subject, key, value)
        self.session.commit()
        self.session.refresh(subject)
        return subject