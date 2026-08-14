from sqlalchemy import select
from sqlalchemy.orm import Session

from ml_service.models.index_explanation import IndexExplanation


class IndexExplanationRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, explanation_id: int) -> IndexExplanation | None:
        return self.session.scalars(
            select(IndexExplanation).where(IndexExplanation.id == explanation_id)
        ).first()

    def get_by_student_index(self, student_index_id: int) -> list[IndexExplanation]:
        return list(self.session.scalars(
            select(IndexExplanation)
            .where(IndexExplanation.student_index_id == student_index_id)
            .order_by(IndexExplanation.rank)
        ).all())

    def save(self, explanation: IndexExplanation) -> IndexExplanation:
        self.session.add(explanation)
        self.session.flush()
        self.session.commit()
        return explanation

    def bulk_save(self, explanations: list[IndexExplanation]) -> list[IndexExplanation]:
        self.session.add_all(explanations)
        self.session.flush()
        self.session.commit()
        return explanations

    def delete(self, explanation_id: int) -> bool:
        explanation = self.get_by_id(explanation_id)
        if explanation is None:
            return False
        self.session.delete(explanation)
        self.session.commit()
        return True