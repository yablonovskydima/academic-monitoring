from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ml_service.models.student_index import StudentIndex


class StudentIndexRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, index_id: int) -> StudentIndex | None:
        return self.session.scalars(
            select(StudentIndex).where(StudentIndex.id == index_id)
        ).first()

    def get_latest_by_student(self, student_id: int) -> StudentIndex | None:
        return self.session.scalars(
            select(StudentIndex)
            .where(StudentIndex.student_id == student_id)
            .order_by(StudentIndex.calculated_at.desc())
        ).first()

    def get_latest_by_student_full(self, student_id: int) -> StudentIndex | None:
        return self.session.scalars(
            select(StudentIndex)
            .options(
                selectinload(StudentIndex.explanations),
                selectinload(StudentIndex.feature_snapshot),
            )
            .where(StudentIndex.student_id == student_id)
            .order_by(StudentIndex.calculated_at.desc())
        ).first()

    def get_history_by_student(self, student_id: int) -> list[StudentIndex]:
        return list(self.session.scalars(
            select(StudentIndex)
            .where(StudentIndex.student_id == student_id)
            .order_by(StudentIndex.calculated_at)
        ).all())

    def save(self, student_index: StudentIndex) -> StudentIndex:
        self.session.add(student_index)
        self.session.flush()
        self.session.commit()
        return student_index

    def bulk_save(self, student_indexes: list[StudentIndex]) -> list[StudentIndex]:
        self.session.add_all(student_indexes)
        self.session.flush()
        self.session.commit()
        return student_indexes

    def delete(self, index_id: int) -> bool:
        student_index = self.get_by_id(index_id)
        if student_index is None:
            return False
        self.session.delete(student_index)
        self.session.commit()
        return True