from sqlalchemy import select
from sqlalchemy.orm import Session

from import_service.models.grade import Grade


class GradeRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, grade_id: int) -> Grade | None:
        return self.session.scalars(
            select(Grade).where(Grade.id == grade_id)
        ).first()

    def get_by_student(self, student_id: int) -> list[Grade]:
        return list(self.session.scalars(
            select(Grade).where(Grade.student_id == student_id)
        ).all())

    def get_by_session(self, class_session_id: int) -> list[Grade]:
        return list(self.session.scalars(
            select(Grade).where(Grade.class_session_id == class_session_id)
        ).all())

    def save(self, grade: Grade) -> Grade:
        self.session.add(grade)
        self.session.commit()
        self.session.refresh(grade)
        return grade

    def bulk_save(self, grades: list[Grade]) -> None:
        self.session.add_all(grades)
        self.session.commit()

    def delete(self, grade_id: int) -> bool:
        grade = self.get_by_id(grade_id)
        if grade is None:
            return False
        self.session.delete(grade)
        self.session.commit()
        return True