from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from import_service.models.faculty import Faculty


class FacultyRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_all(self) -> list[Faculty]:
        return list(self.session.scalars(select(Faculty)).all())

    def get_by_id(self, faculty_id: int) -> Faculty | None:
        return self.session.scalars(
            select(Faculty).where(Faculty.id == faculty_id)
        ).first()

    def get_full_by_id(self, faculty_id: int) -> Faculty | None:
        return self.session.scalars(
            select(Faculty)
            .options(joinedload(Faculty.groups))
            .where(Faculty.id == faculty_id)
        ).unique().first()

    def save(self, faculty: Faculty) -> Faculty:
        self.session.add(faculty)
        self.session.commit()
        self.session.refresh(faculty)
        return faculty

    def bulk_save(self, faculties: list[Faculty]) -> list[Faculty]:
        self.session.add_all(faculties)
        self.session.flush()
        self.session.commit()
        return faculties

    def delete(self, faculty_id: int) -> bool:
        faculty = self.get_by_id(faculty_id)
        if faculty is None:
            return False
        self.session.delete(faculty)
        self.session.commit()
        return True
