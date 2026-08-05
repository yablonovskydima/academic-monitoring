from sqlalchemy.orm import Session

from ml_service.models.index_explanation import IndexExplanation
from ml_service.repositories.index_explanation_repository import IndexExplanationRepository
from ml_service.schemas.index_explanation import IndexExplanationCreate


class IndexExplanationService:
    def __init__(self, db: Session):
        self.repo = IndexExplanationRepository(db)

    def get_by_student_index(self, student_index_id: int) -> list[IndexExplanation]:
        return self.repo.get_by_student_index(student_index_id)

    def create(self, student_index_id: int, data: IndexExplanationCreate) -> IndexExplanation:
        explanation = IndexExplanation(student_index_id=student_index_id, **data.model_dump())
        return self.repo.save(explanation)

    def bulk_create(self, student_index_id: int, items_data: list[IndexExplanationCreate]) -> list[IndexExplanation]:
        explanations = [
            IndexExplanation(student_index_id=student_index_id, **data.model_dump())
            for data in items_data
        ]
        return self.repo.bulk_save(explanations)

    def delete(self, explanation_id: int) -> bool:
        return self.repo.delete(explanation_id)