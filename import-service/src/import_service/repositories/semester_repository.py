from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from import_service.models.semester import Semester


class SemesterRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_all(self) -> list[Semester]:
         return list(self.session.scalars(select(Semester)).all())

    def get_by_id(self, semester_id: int) -> Semester | None:
        return self.session.scalars(
            select(Semester).where(Semester.id == semester_id)
        ).first()

    def get_current(self) -> Semester | None:
        today = date.today()
        return self.session.scalars(
            select(Semester).where(
                Semester.start_date <= today, Semester.end_date >= today
            )
        ).first()

    def save(self, semester: Semester) -> Semester:
        self.session.add(semester)
        self.session.commit()
        self.session.refresh(semester)
        return semester

    def bulk_save(self, semesters: list[Semester]) -> None:
        self.session.add_all(semesters)
        self.session.commit()

    def delete(self, semester_id: int) -> bool:
        semester = self.get_by_id(semester_id)
        if semester is None:
            return False
        self.session.delete(semester)
        self.session.commit()
        return True