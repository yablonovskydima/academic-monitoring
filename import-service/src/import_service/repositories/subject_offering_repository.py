from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from import_service.models.subject_offering import SubjectOffering


class SubjectOfferingRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_full_by_id(self, offering_id: int) -> SubjectOffering | None:
        return self.session.scalars(
            select(SubjectOffering)
            .options(
                joinedload(SubjectOffering.class_sessions),
                joinedload(SubjectOffering.enrollments),
            )
            .where(SubjectOffering.id == offering_id)
        ).unique().first()

    def get_all(self) -> list[SubjectOffering]:
        return list(self.session.scalars(select(SubjectOffering)).all())

    def get_by_id(self, offering_id: int) -> SubjectOffering | None:
        return self.session.scalars(
            select(SubjectOffering).where(SubjectOffering.id == offering_id)
        ).first()

    def get_by_semester(self, semester_id: int) -> list[SubjectOffering]:
        return list(self.session.scalars(
            select(SubjectOffering).where(SubjectOffering.semester_id == semester_id)
        ).all())

    def create(self, offering: SubjectOffering) -> SubjectOffering:
        self.session.add(offering)
        self.session.commit()
        self.session.refresh(offering)
        return offering

    def bulk_create(self, offerings: list[SubjectOffering]) -> None:
        self.session.add_all(offerings)
        self.session.commit()

    def update(self, offering_id: int, **fields) -> SubjectOffering | None:  # todo dto for update
        offering = self.get_by_id(offering_id)
        if offering is None:
            return None
        for key, value in fields.items():
            setattr(offering, key, value)
        self.session.commit()
        self.session.refresh(offering)
        return offering